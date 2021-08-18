from flask import Flask, redirect, url_for, render_template, request, session, flash, Response, send_file
from flask_sqlalchemy import SQLAlchemy
import cv2
import os
import face_recognition
from sklearn import svm
import numpy as np
import pickle
from threading import Thread, Event
import threading
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime
import socket
import sys
import atexit
app = Flask(__name__)


app.secret_key = "shh"
buff="Train model"

# SQL Database Credentials
host = "localhost"
user = "root"
pwd = "123456"
db = "attendance"
filename = ""

# Credentials of the Employee
a_emid = ""
f_name=""
l_name=""

#For training the model file
def training():
	global buff
	print("Running")
	if buff=="Under Training.\nPLease wait.....":
		save()

def save():
    global buff
    print(buff)
    clf = svm.SVC(gamma ='scale')
    encodings=[]
    label=[]
    for i in os.listdir('Employee'):
        print(i)
        for j in os.listdir('Employee/'+i):
            try:
                encodings.append(face_recognition.face_encodings(cv2.imread('Employee/'+i+'/'+j))[0])
                label.append(i)
            except:
                continue
    encodings=np.array(encodings)
    labels=np.array(label)
    clf.fit(encodings,labels)
    pickle.dump(clf,open('model.pickle', 'wb'))
    buff="Train model"
    print("Done training")
    return 

#For creating connection to the database
def create_db_connection(host_name, user_name, user_password, db_name):
    con= None
    try:
        con = mysql.connector.connect(
            host = host_name,
            user = user_name,
            passwd = user_password,
            database = db_name)
        print("MySQL Database connection successful")

    except Error as err:
        print(f"Error: '{err}'")

    return con

#For executing SQL queries
def execute_query(con, query):
    cursor = con.cursor()
    try:
        cursor.execute(query)
        con.commit()
        print("Query Successful")
    except Error as err:
        print(f"Error: '{err}'")
        
#For reading the data from the SQL Table        
def read_query(con, query):
    cursor = con.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        print(result)
        return result
    except Error as err:
        print(f"Error: '{err}'")
        return "Empty"

#For making the folder of photos for employees 
def Roll_no():
    if emid in os.listdir("Employee"):
        pass
    else:
        os.mkdir('Employee/'+str(emid))


#For capturing images of the employee
def Capture():
    global emid
    if emid=="" and f_name=="":
        return
    query = f"insert ignore into Employee values ('{emid}', '{f_name}', '{l_name}');"
    execute_query(connection, query)
    Roll_no()

    cap=cv2.VideoCapture(0)
    captures=0
    

    while True:
        ret,frame=cap.read()
        face=face_recognition.face_locations(frame)
        if len(face):
            y1,x2,y2,x1=face[0]
            cv2.imwrite("Employee/"+str(emid)+"/"+str(captures)+".jpg",frame)
            captures+=1
        key=cv2.waitKey(1)
        if key==27 or captures==100:
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    cap.release()

connection = create_db_connection(host, user, pwd, db)

def server():
	while True:
	    global connection
	        # take the server name and port name 
	    host = '192.168.1.4'
	    port = 5001
	    s = socket.socket(socket.AF_INET,  
	                              socket.SOCK_STREAM)             
	    # bind the socket with server 
	    # and port number 
	    s.bind(('', port))

	    # set maximum connection to 
	    # the socket 
	    s.listen(5)
	    print("Listening")

	    # wait till a client accept 
	    # connection 
	    c, addr = s.accept() 

	    # display client address 
	    print("CONNECTION FROM:", str(addr)) 

	    # send message to the client after  
	    # encoding into binary string 
	    c.send(b"Accepting attendance") 
	    a_emp_id = c.recv(1024).decode()
	    print(a_emp_id)
	    if a_emp_id!='':
	        d_d = str(datetime.now()).split(" ")[0]
	        d_t = str(datetime.now()).split(" ")[1]
	        records = f"Select * from Employee where Employee_ID = '{a_emp_id}';"
	        results = read_query(connection, records)
	        entry = []
	        for res in results:
	            res = list(res)
	            entry.append(res)
	        columns = ["Employe_ID", "First Name", "Last Name", "Date", "Time"]
	        
	        query = f"insert into Emp_Atten values ('{entry[0][0]}', '{entry[0][1]}', '{entry[0][2]}','{d_d}','{d_t}');"
	        execute_query(connection, query)
	        a_emp_id=''
	    
	    c.close()
	return

#exit_event = Event()
#th = Thread(target = server)
#th.start()




#Home page
@app.route("/")
@app.route('/home')
def home():
	global buff
	return render_template("index.html",buff=buff)


#For adding new employee into the database
@app.route('/new', methods=['POST', 'GET'])
def new():
    if request.method =='POST':
        global emid, f_name, l_name
        emid = request.form['empid']
        f_name = request.form['f_name']
        l_name = request.form['l_name']
        if emid=="" or f_name=="":
            a = "Please check your entries"
        else:
            print(emid)
            a = "Employee ID: "+str(emid)+"\nName: "+f_name+" "+l_name
        flash(a)
    global buff
    return render_template("new.html", buff=buff)

#For opening the camera
@app.route("/video")
def add():
    return Response(Capture(), mimetype = 'multipart/x-mixed-replace; boundary=frame')

#For training 
@app.route("/train")
def train():
	global buff
	buff = "Under Training.\nPLease wait....."
	thread = Thread(target = training)
	thread.start()
	return redirect(url_for("home"))


#For checking the lsit of added employees in the database
@app.route("/emp_list")
def emp_list():
    records = "Select * from Employee;"
    
    results = read_query(connection, records)
    from_db = []
    for res in results:
        res = list(res)
        from_db.append(res)
    columns = ["Employe_ID", "First Name", "Last Name"]

    global emp_file
    df = pd.DataFrame(from_db, columns=columns)
    df = df.rename_axis('S.No.', axis="columns")
    df.index+=1
    emp_file = "Employee_list.csv"
    df.to_csv(emp_file)
    print(emp_file)
    return render_template('simple.html',  
        tables=[df.to_html(header="true", classes='table table-striped')], filename= "Employee")


# Checking today's attendance 
@app.route('/atten')
def t_atten():
	global connection
	global atten_file
	connection = create_db_connection(host, user, pwd, db)
	d = str(datetime.now()).split(" ")[0]
	records = f"Select * from Emp_Atten where Date='{d}';"
	results = read_query(connection, records)
	if results=="Empty":
		flash("No attendance record yet")
		return render_template("simple.html", filename = "")
	
	from_db = []
	for res in results:
	    res = list(res)
	    from_db.append(res)
	columns = ["Employe_ID", "First Name", "Last Name", "Date", "Time"]

	
	dfa = pd.DataFrame(from_db, columns=columns)
	dfa = dfa.rename_axis('S.No.', axis="columns")
	dfa.index+=1
	atten_file = "attendance"+d+".csv"
	dfa.to_csv(atten_file)
	print(atten_file)
	return render_template('simple_atten.html',  
	    tables=[dfa.to_html(header="true", classes='table table-striped')] , filename = "attendance")
emp_file = ""
atten_file = ""
#For removing the unwanted files from the server
def remove_file():
	global emp_file, atten_file
	try:
		os.remove(emp_file)
		os.remove(atten_file)
		return
	except:
		return


#Downlaod button for the csv files
@app.route('/download')
def download_file():
    global emp_file
    return send_file(emp_file, as_attachment=True)

@app.route('/download_atten')
def download_atten():
    global atten_file
    return send_file(atten_file, as_attachment=True)


my_thread = Thread(target = server, daemon=True)
my_thread.start()
if __name__ == "__main__":
	print("Starting webpage")
	app.run(debug = True)
	atexit.register(remove_file())
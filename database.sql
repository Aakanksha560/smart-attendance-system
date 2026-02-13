CREATE DATABASE smart_attendance;
USE smart_attendance;

CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100),
  username VARCHAR(50),
  password VARCHAR(50),
  role ENUM('teacher','student')
);

CREATE TABLE subjects (
  id INT PRIMARY KEY AUTO_INCREMENT,
  subject_name VARCHAR(100)
);

CREATE TABLE students (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT,
  class VARCHAR(50),
  parent_phone VARCHAR(15)
);

CREATE TABLE qr_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  subject_id INT,
  session_code VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME
);

CREATE TABLE attendance (
  id INT PRIMARY KEY AUTO_INCREMENT,
  student_id INT,
  subject_id INT,
  session_id INT,
  status VARCHAR(20),
  marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SAMPLE DATA
INSERT INTO users VALUES
(1,'Teacher','teacher01','1234','teacher'),
(2,'Student','student01','1234','student');

INSERT INTO students VALUES (1,2,'BCA','+919876543210');

INSERT INTO subjects(subject_name) VALUES
('DBMS'),('AI'),('Web Technology'),('Cloud Computing');

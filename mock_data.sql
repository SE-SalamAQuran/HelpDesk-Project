USE helpdesk_db;

-- USERS
INSERT INTO `USER` (ID, Full_Name, Email, Password, Role) VALUES
(1, 'Ahmad Khalil', 'ahmad@company.com', 'password1', 'admin'),
(2, 'Omar Nasser', 'omar.it@company.com', 'password2', 'IT'),
(3, 'Sara Ali', 'sara.it@company.com', 'password3', 'IT'),
(4, 'Mohammad Hasan', 'mohammad@company.com', 'password4', 'employee'),
(5, 'Lina Ahmad', 'lina@company.com', 'password5', 'employee'),
(6, 'Yousef Sami', 'yousef@company.com', 'password6', 'employee');


-- TICKETS
INSERT INTO TICKET
(ID, Title, Description, Created_By, Assigned_To, Category, Status, Priority)
VALUES
(1, 'Laptop Not Connecting to WiFi',
 'Employee cannot connect the company laptop to WiFi.',
 4, 2, 'IT', 'In Progress', 'High'),

(2, 'Forgot Email Password',
 'Employee forgot the password for the company email.',
 5, 3, 'IT', 'Resolved', 'Medium'),

(3, 'Request New Mouse',
 'Employee needs a new wireless mouse.',
 6, 2, 'IT', 'Open', 'Low'),

(4, 'Printer Not Working',
 'Office printer is not printing documents.',
 4, 3, 'IT', 'In Progress', 'High'),

(5, 'Vacation Request Problem',
 'Employee cannot submit vacation request.',
 5, NULL, 'HR', 'Open', 'Medium');


-- COMMENTS
INSERT INTO COMMENT
(ID, Comment_Text, User_ID, Ticket_ID)
VALUES
(1, 'The problem started this morning.', 4, 1),
(2, 'I will check the network settings.', 2, 1),
(3, 'Password has been reset successfully.', 3, 2),
(4, 'Thank you, the email is working now.', 5, 2),
(5, 'Please provide the mouse model.', 2, 3);


-- ATTACHMENTS
INSERT INTO ATTACHMENT
(ID, File_Name, File_Path, Ticket_ID, Uploaded_By)
VALUES
(1, 'wifi_error.png', '/uploads/wifi_error.png', 1, 4),
(2, 'printer_error.jpg', '/uploads/printer_error.jpg', 4, 4),
(3, 'vacation_request.pdf', '/uploads/vacation_request.pdf', 5, 5);


-- CHANGE LOG
INSERT INTO CHANGE_LOG
(ID, Field_Name, Old_Value, New_Value, Ticket_ID, Changed_By)
VALUES
(1, 'Status', 'Open', 'In Progress', 1, 2),
(2, 'Assigned_To', NULL, '2', 1, 1),
(3, 'Status', 'Open', 'Resolved', 2, 3),
(4, 'Priority', 'Medium', 'High', 4, 3);
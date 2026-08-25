CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Full_Name VARCHAR(100) NOT NULL,
    Email VARCHAR(150) NOT NULL UNIQUE,
    Password_Hash VARCHAR(255) NOT NULL,
    Role ENUM('admin', 'IT_employee','employee') NOT NULL,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Modified_At DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
CREATE TABLE Ticket (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Title VARCHAR(200) NOT NULL,
    Description TEXT,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    Created_By INT NOT NULL,
    Assigned_To INT NULL,
    Category ENUM('hardware', 'software', 'network', 'other') NOT NULL,
    Status ENUM('open', 'in_progress', 'resolved', 'closed', 'reopened') NOT NULL,
    Priority ENUM('low', 'medium', 'high', 'critical') NOT NULL DEFAULT 'medium',
    FOREIGN KEY (Created_By) REFERENCES users(id),
    FOREIGN KEY (Assigned_To) REFERENCES users(id)
);
CREATE TABLE Comment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Comment_Text TEXT NOT NULL,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    Ticket_ID INT NOT NULL,
    User_ID INT NOT NULL,
    FOREIGN KEY (Ticket_ID) REFERENCES Ticket(id) ON DELETE CASCADE,
    FOREIGN KEY (User_ID) REFERENCES users(id)
);
CREATE TABLE Attachment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    File_Name VARCHAR(255) NOT NULL,
    File_Path VARCHAR(500) NOT NULL,
    Ticket_ID INT NOT NULL,
    Uploaded_By INT NOT NULL,
    Uploaded_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Ticket_ID) REFERENCES Ticket(id) ON DELETE CASCADE,
    FOREIGN KEY (Uploaded_By) REFERENCES users(id)
);
CREATE TABLE Ticket_History (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Field_Name VARCHAR(100) NOT NULL,
    Old_Value TEXT,
    New_Value TEXT,
    Ticket_ID INT NOT NULL,
    Changed_By INT NOT NULL,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Ticket_ID) REFERENCES Ticket(id) ON DELETE CASCADE,
    FOREIGN KEY (Changed_By) REFERENCES users(id)
);
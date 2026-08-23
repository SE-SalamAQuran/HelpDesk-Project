CREATE DATABASE IF NOT EXISTS helpdesk_db;
USE helpdesk_db;


-- =========================
-- USER
-- =========================
CREATE TABLE `USER` (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Full_Name VARCHAR(100) NOT NULL,
    Email VARCHAR(150) NOT NULL UNIQUE,
    Password VARCHAR(255) NOT NULL,
    Role ENUM('admin', 'IT', 'employee') NOT NULL,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP
);


-- =========================
-- TICKET
-- =========================
CREATE TABLE TICKET (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Title VARCHAR(255) NOT NULL,
    Description MEDIUMTEXT,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Updated_At DATETIME DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    Created_By INT NOT NULL,
    Assigned_To INT NULL,
    Category ENUM('IT','HR') NOT NULL DEFAULT 'HR',
    Status ENUM('Open','In Progress','Resolved','Closed','Reopened') NOT NULL DEFAULT 'Open',
    Priority ENUM('Low','Medium','High','Critical') NOT NULL DEFAULT 'Medium',
    FOREIGN KEY (Created_By)
        REFERENCES `USER`(ID),

    FOREIGN KEY (Assigned_To)
        REFERENCES `USER`(ID)
        ON DELETE SET NULL
);


-- =========================
-- COMMENT
-- =========================
CREATE TABLE COMMENT (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Comment_Text TEXT NOT NULL,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Modified_At DATETIME DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    User_ID INT NOT NULL,
    Ticket_ID INT NOT NULL,
    FOREIGN KEY (User_ID)
        REFERENCES `USER`(ID),

    FOREIGN KEY (Ticket_ID)
        REFERENCES TICKET(ID)
        ON DELETE CASCADE
);


-- =========================
-- ATTACHMENT
-- =========================
CREATE TABLE ATTACHMENT (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    File_Name VARCHAR(255) NOT NULL,
    File_Path VARCHAR(500) NOT NULL,
    Ticket_ID INT NOT NULL,
    Uploaded_By INT NOT NULL,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Ticket_ID)
        REFERENCES TICKET(ID)
        ON DELETE CASCADE,

    FOREIGN KEY (Uploaded_By)
        REFERENCES `USER`(ID)
);


-- =========================
-- CHANGE LOG
-- =========================
CREATE TABLE CHANGE_LOG (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Field_Name VARCHAR(100) NOT NULL,
    Old_Value VARCHAR(255),
    New_Value VARCHAR(255),
    Ticket_ID INT NOT NULL,
    Changed_By INT NOT NULL,
    Changed_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Ticket_ID)
        REFERENCES TICKET(ID)
        ON DELETE CASCADE,

    FOREIGN KEY (Changed_By)
        REFERENCES `USER`(ID)
);
from app import db

attachments = [
    {
        "ID": 1,
        "File_Name": "wifi_error.png",
        "File_Path": "/uploads/tickets/1/wifi_error.png",
        "Ticket_ID": 1,
        "Uploaded_By": 4
    },
    {
        "ID": 2,
        "File_Name": "printer_error.jpg",
        "File_Path": "/uploads/tickets/4/printer_error.jpg",
        "Ticket_ID": 4,
        "Uploaded_By": 4
    },
    {
        "ID": 3,
        "File_Name": "vacation_request.pdf",
        "File_Path": "/uploads/tickets/5/vacation_request.pdf",
        "Ticket_ID": 5,
        "Uploaded_By": 5
    },
    {
        "ID": 4,
        "File_Name": "slow_pc.png",
        "File_Path": "/uploads/tickets/6/slow_pc.png",
        "Ticket_ID": 6,
        "Uploaded_By": 6
    },
    {
        "ID": 5,
        "File_Name": "office_error.png",
        "File_Path": "/uploads/tickets/8/office_error.png",
        "Ticket_ID": 8,
        "Uploaded_By": 5
    },
    {
        "ID": 6,
        "File_Name": "office_license.pdf",
        "File_Path": "/uploads/tickets/8/office_license.pdf",
        "Ticket_ID": 8,
        "Uploaded_By": 3
    }
]

for attachment in attachments:
    attachment_id = str(attachment["ID"])

    db.collection("attachments").document(attachment_id).set(attachment)

print("Attachments uploaded successfully!")
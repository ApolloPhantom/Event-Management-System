/* CREATE TABLE Organizer(
    O_ID int PRIMARY KEY,
    Name varchar(100),
    Password varchar(20),
    Security_Key int UNIQUE
); */

/* CREATE TABLE Venue(
    V_Id int PRIMARY KEY,
    Name varchar(100),
    Address varchar(300),
    Rent int,
    Capacity int
);
*/
/* 
CREATE TABLE Event_Schedule(
    ES_Id int PRIMARY KEY,
    E_Id int,
    Programme_Name varchar(100),
    No_of_Participants int,
    Host_Name varchar(100),
    Amount_required int,
    Status varchar(1)
);

CREATE TABLE Sponsor(
    S_Id int PRIMARY KEY,
    E_Id int,
    Name varchar(200),
    Fund int,
    Company_Name varchar(100)
);

CREATE TABLE Budget(
    B_Id int PRIMARY KEY,
    E_Id int,
    Amount int
);

CREATE TABLE Attendee(
    A_Id int PRIMARY KEY,
    E_Id int,
    Name varchar(100),
    Specialization varchar(20),
    Phone_No int,
    E_Mail varchar(100)
);

CREATE TABLE Payment(
    P_Id int PRIMARY KEY,
    DOT date,
    Amount int,
    Bank_id int
);

CREATE TABLE Bank(
    Bank_id int PRIMARY KEY,
    PIN int,
    Total_Amount int
); */

/* CREATE TABLE Transac(
    B_Id int PRIMARY KEY,
    P_Id int,
    DOT date,
    Amount int
); */

/* CREATE TABLE Event(
    E_Id int PRIMARY KEY,
    Name varchar(100),
    S_Date date,
    E_Date date,
    Hosting_Dept varchar(100),
    No_of_Schedules int,
    Starting Capital int,
    Img_Link varchar(1000)
);  */

/* INSERT INTO Organizer VALUES
(1000,"Admin","Admin",123),
(1001,"Back","Back",234);

INSERT INTO Venue VALUES
(1,"I_Hall","Lobby I",10000,200),
(2,"A_Hall","Hostel Ground",20000,300);

INSERT INTO Event VALUES
(1,"Sphuran","2024-04-10","2024-04-13","ME",3,20000,''),
(2,"Rebecca","2024-04-16","2024-04-19","ALL",4,90000,''); */

/* INSERT INTO Event_Schedule VALUES
(1,1,"Contest 1",5,"P.Sharma",10000,"N"),
(2,1,"Contest 2",3,"None",10000,"N"); */

/* alter table Event
add V_Id int; */

/* INSERT INTO BANK VALUES
(1,111,9999999); */

/* update Event set 
Img_Link = "C:\Users\shyam\OneDrive\Desktop\SE_Project\static\68585.jpg"
where E_Id in (1,2); */

delete from Budget where B_Id = 311;
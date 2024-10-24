import csv
import random
from datetime import datetime, timedelta

# Function to generate random dates
def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

# Sample data for fields
event_names = [
    "Tech Symposium", "Annual Meeting", "Cultural Fest", "Science Expo", 
    "Alumni Meet", "Sports Day", "Hackathon", "Seminar"
]
departments = [
    "Computer Science", "Mechanical Engineering", "Electrical Engineering", 
    "Civil Engineering", "Chemical Engineering", "Physics Department"
]

# Date range for the events (let's say within the year 2024)
start_date_range = datetime(2024, 1, 1)
end_date_range = datetime(2024, 12, 31)

# Generate sample data for 10 events
data = []
for i in range(1, 11):
    event_name = random.choice(event_names)
    s_date = random_date(start_date_range, end_date_range).strftime('%Y-%m-%d')
    e_date = random_date(datetime.strptime(s_date, '%Y-%m-%d'), end_date_range).strftime('%Y-%m-%d')
    dept = random.choice(departments)
    schedules = random.randint(1, 5)
    starting_capital = round(random.uniform(5000, 100000), 2)
    v_id = random.randint(100, 500)
    
    # Append the data for each row
    data.append([i, event_name, s_date, e_date, dept, schedules, starting_capital, v_id])

# Write the data to a CSV file
headers = ["E_Id", "Name", "S_Date", "E_Date", "Hosting_Dept", "No_of_Schedules", "Starting_Capital", "V_Id"]
with open('event_data.csv', mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)
    writer.writerows(data)

print("CSV file created with sample data.")

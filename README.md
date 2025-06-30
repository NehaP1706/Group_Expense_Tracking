# Objective

Develop a web application that enables users to track, manage, and settle shared expenses within a group, such as during trips, events, or shared living situations. The app should simplify expense tracking, provide clear visibility of who owes whom, and streamline settlement
processes, ensuring a fair and hassle-free experience for all group members.

# API Endpoints

1. ```'/signup'``` : To fill in user details for registration.
2. ```'/login'``` : To specify user for a session.
3. ```'/api/profile/:userId'``` : To fetch user details, debt, groups and transaction history.
4. ```'/api/group/:groupId'``` : To fetch the various events and activities under a certain group.
5. ```'/api/groupsForUser'``` : To list (as hyperlinks) the various groups a user created or is a part of.
6. ```'/api/groups'``` : To list the groups (on the profile page).
7. ```'api/group/:groupId/addEvent'``` : To add a new event to a group (specifying details, expenses and people involved).
8. ```'/api/transactions'``` : To handle the transactions.
9. ```'/api/uploadReceiptOnly'``` : To handle the receipts uploaded for review by owedTo and owedBy.
10. ```'/api/markTransactionPaid'``` : To settle payments.
11. ```'/api/groups/:groupId/updateMembers'``` : To update people involved in the group.

# How To Run

Clone the repository and install the necessary dependencies, if necessary.
Set up a .env file with connection to a MongoDB atlas account (variable ``` MONGOURI ```) and port for listening (default at ``` 3000 ```).
Then, run the command:

``` node server.js  ```

Open a web browser and access  ``` http://localhost:3000/login ``` or ``` httpe://localhost:3000/signup ```

# Further Improvements (Thinking Ahead)

1. Verify receipts uploaded for relevance.
2. Integrate payment gateway UPIs to settle payments in the app.
3. Apply currency conversions during transactions.
4. Add CSS styles for aesthetic.
5. Allow profile picture and event/Group pictures for presentability.
6. Allow drop-downs instead of typing userIds while creating groups or editin members.

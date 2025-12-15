# User queries
GET_USER = "select * from User where username = %s"

CREATE_USER = """
    insert into User (username, first_name, last_name, mobile, currency, password)
    values (%s, %s, %s, %s, %s, %s)
"""

# Group queries
# Much simpler: Join by group_name only
GET_GROUPS_FOR_USER = """
    select g.*, u.first_name as creator_first_name, u.last_name as creator_last_name
    from `Group` g
    join User u on g.created_by = u.username
    where g.group_name in (
        select group_name from GroupMember where username = %s
    )
    order by g.created_at desc
"""

GET_GROUP_MEMBERS = """
    select u.* from User u
    join GroupMember gm on u.username = gm.username
    where gm.group_name = %s
"""

CREATE_GROUP = """
    insert into `Group` (group_name, created_by, duration)
    values (%s, %s, %s)
"""

ADD_GROUP_MEMBER = """
    insert into GroupMember (group_name, username) values (%s, %s)
"""

DELETE_GROUP_MEMBERS = """
    delete from GroupMember where group_name = %s
"""

# Event queries
# Identify by group_name only
GET_EVENTS_FOR_GROUP = """
    select * from Event where group_name = %s order by created_at desc
"""

CREATE_EVENT = """
    insert into Event (group_name, event_name, created_by, description, duration)
    values (%s, %s, %s, %s, %s)
"""

# Transaction queries
GET_TRANSACTIONS_FOR_EVENT = """
    select t.*, 
           u1.first_name as owed_by_first, u1.last_name as owed_by_last,
           u2.first_name as owed_to_first, u2.last_name as owed_to_last
    from Transaction t
    join User u1 on t.owed_by = u1.username
    join User u2 on t.owed_to = u2.username
    where t.group_name = %s and t.event_name = %s
    order by t.timestamp desc
"""

GET_TRANSACTION_BY_DETAILS = """
    select * from Transaction
    where group_name = %s and event_name = %s 
    and timestamp = %s and owed_by = %s and owed_to = %s
"""

CREATE_TRANSACTION = """
    insert into Transaction (group_name, event_name, created_by, owed_by, owed_to, amount, reason, timestamp)
    values (%s, %s, %s, %s, %s, %s, %s, %s)
"""

MARK_TRANSACTION_PAID = "update Transaction set is_paid = true where transaction_id = %s"

UPDATE_TRANSACTION_RECEIPT = "update Transaction set receipt_path = %s where transaction_id = %s"

GET_PAID_TRANSACTIONS_FOR_USER = """
    select * from PaidTransaction 
    where owed_by = %s or owed_to = %s
    order by payment_timestamp desc
"""

# Chatbot queries
SAVE_CHAT_MESSAGE = "insert into ChatMessage (username, sender, message) values (%s, %s, %s)"
GET_CHAT_HISTORY = "select sender, message, timestamp from ChatMessage where username = %s order by timestamp desc limit %s"
SAVE_EXTRACTED_INFO = "insert into ChatExtracted (username, category, value, context) values (%s, %s, %s, %s)"
GET_EXTRACTED_INFO = "select category, value, context, timestamp from ChatExtracted where username = %s and is_used = false order by timestamp desc"
MARK_EXTRACTED_USED = "update ChatExtracted set is_used = true where extract_id = %s"

# Add these to your queries.py file

# Trip queries
CREATE_TRIP = """
    insert into Trip (trip_name, group_name, created_by, travel_class)
    values (%s, %s, %s, %s)
"""

GET_TRIP_BY_ID = """
    select * from Trip where trip_id = %s
"""

GET_TRIPS_FOR_USER = """
    select t.* from Trip t
    where t.created_by = %s or t.group_name in (
        select group_name from GroupMember where username = %s
    )
    order by t.created_at desc
"""

GET_TRIPS_FOR_GROUP = """
    select * from Trip where group_name = %s order by created_at desc
"""

# Destination queries
ADD_DESTINATION = """
    insert into TripDestination (trip_id, city, country, airport_code, latitude, longitude, visit_order, arrival_date, departure_date)
    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

GET_DESTINATIONS_FOR_TRIP = """
    select * from TripDestination where trip_id = %s order by visit_order
"""

# Route queries
ADD_ROUTE = """
    insert into TripRoute (trip_id, from_destination_id, to_destination_id, flight_cost, airline, flight_number, departure_time, arrival_time)
    values (%s, %s, %s, %s, %s, %s, %s, %s)
"""

GET_ROUTES_FOR_TRIP = """
    select r.*, 
           d1.city as from_city, d1.airport_code as from_airport,
           d2.city as to_city, d2.airport_code as to_airport
    from TripRoute r
    join TripDestination d1 on r.from_destination_id = d1.destination_id
    join TripDestination d2 on r.to_destination_id = d2.destination_id
    where r.trip_id = %s
    order by r.departure_time
"""

# Pathway queries
SAVE_PATHWAY = """
    insert into TripPathways (trip_id, path_sequence, total_cost, total_ways, is_optimal)
    values (%s, %s, %s, %s, %s)
"""

GET_PATHWAYS_FOR_TRIP = """
    select * from TripPathways where trip_id = %s order by total_cost
"""

GET_OPTIMAL_PATHWAY = """
    select * from TripPathways where trip_id = %s and is_optimal = true limit 1
"""
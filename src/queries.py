# User queries
GET_USER = "SELECT * FROM User WHERE username = %s"

CREATE_USER = """
    INSERT INTO User (username, first_name, last_name, mobile, currency, password)
    VALUES (%s, %s, %s, %s, %s, %s)
"""

# Group queries
GET_GROUPS_FOR_USER = """
    SELECT g.*, u.first_name as creator_first_name, u.last_name as creator_last_name
    FROM `Group` g
    JOIN User u ON g.created_by = u.username
    WHERE g.group_name IN (
        SELECT group_name FROM GroupMember WHERE username = %s
    )
    ORDER BY g.created_at DESC
"""

GET_GROUP_MEMBERS = """
    SELECT u.* FROM User u
    JOIN GroupMember gm ON u.username = gm.username
    WHERE gm.group_name = %s
"""

CREATE_GROUP = """
    INSERT INTO `Group` (group_name, created_by, duration)
    VALUES (%s, %s, %s)
"""

ADD_GROUP_MEMBER = """
    INSERT INTO GroupMember (group_name, username) VALUES (%s, %s)
"""

DELETE_GROUP_MEMBERS = """
    DELETE FROM GroupMember WHERE group_name = %s
"""

# Event queries
GET_EVENTS_FOR_GROUP = """
    SELECT * FROM Event WHERE group_name = %s ORDER BY created_at DESC
"""

CREATE_EVENT = """
    INSERT INTO Event (group_name, event_name, created_by, description, duration)
    VALUES (%s, %s, %s, %s, %s)
"""

# Transaction queries
GET_TRANSACTIONS_FOR_EVENT = """
    SELECT t.*, 
           u1.first_name as owed_by_first, u1.last_name as owed_by_last,
           u2.first_name as owed_to_first, u2.last_name as owed_to_last
    FROM Transaction t
    JOIN User u1 ON t.owed_by = u1.username
    JOIN User u2 ON t.owed_to = u2.username
    WHERE t.group_name = %s AND t.event_name = %s
    ORDER BY t.timestamp DESC
"""

GET_TRANSACTION_BY_DETAILS = """
    SELECT * FROM Transaction
    WHERE group_name = %s AND event_name = %s 
    AND timestamp = %s AND owed_by = %s AND owed_to = %s
"""

CREATE_TRANSACTION = """
    INSERT INTO Transaction (group_name, event_name, created_by, owed_by, owed_to, amount, reason, timestamp)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

MARK_TRANSACTION_PAID = "UPDATE Transaction SET is_paid = TRUE WHERE transaction_id = %s"

UPDATE_TRANSACTION_RECEIPT = "UPDATE Transaction SET receipt_path = %s WHERE transaction_id = %s"

GET_PAID_TRANSACTIONS_FOR_USER = """
    SELECT * FROM PaidTransaction 
    WHERE owed_by = %s OR owed_to = %s
    ORDER BY payment_timestamp DESC
"""

# Trip queries
CREATE_TRIP = """
    INSERT INTO Trip (trip_name, group_name, created_by, travel_class)
    VALUES (%s, %s, %s, %s)
"""

GET_TRIP_BY_ID = """
    SELECT * FROM Trip WHERE trip_id = %s
"""

GET_TRIPS_FOR_USER = """
    SELECT t.* FROM Trip t
    WHERE t.created_by = %s OR t.group_name IN (
        SELECT group_name FROM GroupMember WHERE username = %s
    )
    ORDER BY t.created_at DESC
"""

GET_TRIPS_FOR_GROUP = """
    SELECT * FROM Trip WHERE group_name = %s ORDER BY created_at DESC
"""

# Destination queries
ADD_DESTINATION = """
    INSERT INTO TripDestination (trip_id, city, country, airport_code, latitude, longitude, visit_order, arrival_date, departure_date)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

GET_DESTINATIONS_FOR_TRIP = """
    SELECT * FROM TripDestination WHERE trip_id = %s ORDER BY visit_order
"""

# Route queries
ADD_ROUTE = """
    INSERT INTO TripRoute (trip_id, from_destination_id, to_destination_id, flight_cost, airline, flight_number, departure_time, arrival_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

GET_ROUTES_FOR_TRIP = """
    SELECT r.*, 
           d1.city as from_city, d1.airport_code as from_airport,
           d2.city as to_city, d2.airport_code as to_airport
    FROM TripRoute r
    JOIN TripDestination d1 ON r.from_destination_id = d1.destination_id
    JOIN TripDestination d2 ON r.to_destination_id = d2.destination_id
    WHERE r.trip_id = %s
    ORDER BY r.departure_time
"""

# Pathway queries
SAVE_PATHWAY = """
    INSERT INTO TripPathways (trip_id, path_sequence, total_cost, total_ways, is_optimal)
    VALUES (%s, %s, %s, %s, %s)
"""

GET_PATHWAYS_FOR_TRIP = """
    SELECT * FROM TripPathways WHERE trip_id = %s ORDER BY total_cost
"""

GET_OPTIMAL_PATHWAY = """
    SELECT * FROM TripPathways WHERE trip_id = %s AND is_optimal = TRUE LIMIT 1
"""

# Chatbot queries (FIXED - using user_id consistently)
SAVE_CHAT_MESSAGE = """
    INSERT INTO ChatMessage (user_id, sender, message)
    VALUES (%s, %s, %s)
"""

GET_CHAT_HISTORY = """
    SELECT sender, message, timestamp
    FROM ChatMessage
    WHERE user_id = %s
    ORDER BY timestamp DESC
    LIMIT %s
"""

SAVE_EXTRACTED_INFO = """
    INSERT INTO ExtractedInfo (user_id, category, value, context)
    VALUES (%s, %s, %s, %s)
"""

GET_EXTRACTED_INFO = """
    SELECT category, value, context, timestamp
    FROM ExtractedInfo
    WHERE user_id = %s AND used = 0
    ORDER BY timestamp DESC
"""

MARK_EXTRACTED_INFO_USED = """
    UPDATE ExtractedInfo
    SET used = 1
    WHERE user_id = %s AND category = %s
"""
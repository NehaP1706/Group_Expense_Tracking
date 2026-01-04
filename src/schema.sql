begin;
drop database if exists expense_tracker;
create database expense_tracker;
use expense_tracker;

create table if not exists User (
    username varchar(100) primary key,
    first_name varchar(100) not null,
    last_name varchar(100) not null,
    mobile varchar(20) not null,
    currency varchar(10) not null default 'INR',
    password varchar(255) not null,
    debt decimal(10, 2) not null default 0.00
);

create table if not exists `Group` (
    group_name varchar(200) primary key,
    created_by varchar(100) not null,
    duration varchar(100),
    created_at timestamp not null default current_timestamp,
    foreign key (created_by) references User(username) on update cascade on delete cascade
);

create table if not exists GroupMember (
    group_name varchar(200) not null,
    username varchar(100) not null,
    primary key (group_name, username),
    foreign key (group_name) references `Group`(group_name) on update cascade on delete cascade,
    foreign key (username) references User(username) on update cascade on delete cascade
);

create table if not exists Event (
    group_name varchar(200) not null,
    event_name varchar(200) not null,
    created_by varchar(100) not null,
    description text,
    duration varchar(100),
    created_at timestamp not null default current_timestamp,
    primary key (group_name, event_name),
    foreign key (group_name) references `Group`(group_name) on update cascade on delete cascade
);

create table if not exists Transaction (
    transaction_id int primary key auto_increment,
    group_name varchar(200) not null,
    event_name varchar(200) not null,
    created_by varchar(100) not null,
    owed_by varchar(100) not null,
    owed_to varchar(100) not null,
    amount decimal(10, 2) not null,
    reason varchar(255),
    timestamp timestamp not null default current_timestamp,
    is_paid boolean not null default false,
    receipt_path varchar(500),
    foreign key (group_name, event_name) references Event(group_name, event_name) on update cascade on delete cascade,
    foreign key (owed_by) references User(username) on update cascade on delete cascade,
    foreign key (owed_to) references User(username) on update cascade on delete cascade
);

create table if not exists PaidTransaction (
    paid_id int primary key auto_increment,
    transaction_id int not null unique,
    amount decimal(10, 2) not null,
    currency varchar(10) not null,
    owed_by varchar(100) not null,
    owed_to varchar(100) not null,
    reason varchar(255),
    payment_timestamp timestamp not null default current_timestamp,
    foreign key (transaction_id) references Transaction(transaction_id) on update cascade on delete cascade,
    foreign key (owed_by) references User(username) on update cascade on delete cascade,
    foreign key (owed_to) references User(username) on update cascade on delete cascade
);

-- Triggers
DROP TRIGGER IF EXISTS after_transaction_insert;
DROP TRIGGER IF EXISTS after_transaction_paid;

delimiter //

create trigger after_transaction_insert
after insert on Transaction
for each row
begin
    update User
    set debt = debt + new.amount
    where username = new.owed_by;
end; //

create trigger after_transaction_paid
after update on Transaction
for each row
begin
    if new.is_paid = true and old.is_paid = false then
        update User
        set debt = debt - new.amount
        where username = new.owed_by;
        
        insert into PaidTransaction (transaction_id, amount, currency, owed_by, owed_to, reason, payment_timestamp)
        select new.transaction_id, new.amount, 
               (select currency from User where username = new.owed_by limit 1),
               new.owed_by, new.owed_to, new.reason, new.timestamp;
    end if;
end; //

delimiter ;

-- Trip planning tables
create table if not exists Trip (
    trip_id int primary key auto_increment,
    trip_name varchar(200) not null,
    group_name varchar(200),
    created_by varchar(100) not null,
    travel_class enum('economy', 'business', 'first') default 'economy',
    created_at timestamp not null default current_timestamp,
    foreign key (group_name) references `Group`(group_name) on update cascade on delete set null,
    foreign key (created_by) references User(username) on update cascade on delete cascade
);

create table if not exists TripDestination (
    destination_id int primary key auto_increment,
    trip_id int not null,
    city varchar(100) not null,
    country varchar(100) not null,
    airport_code varchar(10),
    latitude decimal(10, 8),
    longitude decimal(11, 8),
    visit_order int not null,
    arrival_date datetime,
    departure_date datetime,
    foreign key (trip_id) references Trip(trip_id) on update cascade on delete cascade
);

create table if not exists TripRoute (
    route_id int primary key auto_increment,
    trip_id int not null,
    from_destination_id int not null,
    to_destination_id int not null,
    flight_cost decimal(10, 2),
    airline varchar(100),
    flight_number varchar(20),
    departure_time datetime,
    arrival_time datetime,
    foreign key (trip_id) references Trip(trip_id) on update cascade on delete cascade,
    foreign key (from_destination_id) references TripDestination(destination_id) on update cascade on delete cascade,
    foreign key (to_destination_id) references TripDestination(destination_id) on update cascade on delete cascade
);

create table if not exists TripPathways (
    pathway_id int primary key auto_increment,
    trip_id int not null,
    path_sequence text not null,
    total_cost decimal(10, 2),
    total_ways int,
    is_optimal boolean default false,
    foreign key (trip_id) references Trip(trip_id) on update cascade on delete cascade
);

-- Chatbot State Management (FIXED - no duplicates)
CREATE TABLE IF NOT EXISTS ChatbotState (
    user_id VARCHAR(100) PRIMARY KEY,
    state VARCHAR(50) NOT NULL DEFAULT 'menu',
    state_data JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(username) ON DELETE CASCADE
);

-- Chat Message History (FIXED - single definition)
CREATE TABLE IF NOT EXISTS ChatMessage (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    sender ENUM('user', 'bot') NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(username) ON DELETE CASCADE,
    INDEX idx_user_timestamp (user_id, timestamp)
);

-- Extracted Information Storage
CREATE TABLE IF NOT EXISTS ExtractedInfo (
    info_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    context TEXT,
    used BOOLEAN DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(username) ON DELETE CASCADE,
    INDEX idx_user_category (user_id, category)
);

commit;
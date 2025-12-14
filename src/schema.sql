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
    group_name varchar(200) primary key, -- GLOBAL PRIMARY KEY
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
    created_by varchar(100) not null, -- Metadata only
    description text,
    duration varchar(100),
    created_at timestamp not null default current_timestamp,
    -- PK is Group + Event Name
    primary key (group_name, event_name),
    foreign key (group_name) references `Group`(group_name) on update cascade on delete cascade
);

create table if not exists Transaction (
    transaction_id int primary key auto_increment,
    group_name varchar(200) not null,
    event_name varchar(200) not null,
    created_by varchar(100) not null, -- Metadata
    owed_by varchar(100) not null,
    owed_to varchar(100) not null,
    amount decimal(10, 2) not null,
    reason varchar(255),
    timestamp timestamp not null default current_timestamp,
    is_paid boolean not null default false,
    receipt_path varchar(500),
    -- Link to Event
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

-- Triggers (Debt calculation)
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

-- Chat tables
create table if not exists ChatMessage (
    message_id int primary key auto_increment,
    username varchar(100) not null,
    sender enum('user', 'bot') not null,
    message text not null,
    timestamp timestamp not null default current_timestamp,
    foreign key (username) references User(username) on update cascade on delete cascade
);

create table if not exists ChatExtracted (
    extract_id int primary key auto_increment,
    username varchar(100) not null,
    category enum('place', 'split_rule', 'reminder', 'task', 'amount', 'event') not null,
    value text not null,
    context text,
    timestamp timestamp not null default current_timestamp,
    is_used boolean not null default false,
    foreign key (username) references User(username) on update cascade on delete cascade
);

commit;
CREATE DATABASE IF NOT EXISTS fc_donation;
USE fc_donation;

DROP TABLE IF EXISTS contact_messages;
DROP TABLE IF EXISTS donation_requests;
DROP TABLE IF EXISTS donations;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('donor','receiver','admin') NOT NULL DEFAULT 'donor',
    phone VARCHAR(30),
    address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE donations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    donation_type ENUM('Food','Clothes') NOT NULL,
    item_name VARCHAR(120) NOT NULL,
    quantity INT NOT NULL,
    size VARCHAR(30),
    description TEXT,
    contact_phone VARCHAR(30),
    `condition` VARCHAR(50),
    pickup_location VARCHAR(255),
    available_date DATETIME NULL,
    status VARCHAR(30) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE donation_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    request_type ENUM('Food','Clothes') NOT NULL,
    item_name VARCHAR(120) NOT NULL,
    quantity INT NOT NULL,
    size VARCHAR(30),
    reason VARCHAR(255),
    address VARCHAR(255),
    contact_phone VARCHAR(30),
    people_count INT,
    needed_by DATETIME NULL,
    description TEXT,
    status VARCHAR(30) DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE contact_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    subject VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Demo accounts: password for all three is password123.
-- The password values are Werkzeug hashes, not plain-text passwords.
INSERT INTO users (name, email, password, role, phone, address) VALUES
('Sample Donor', 'donor@example.com', 'pbkdf2:sha256:600000$fcstudent$0e0d9ead5d2d3cae406008d876eae4933d45c83223b43b04eb23d0a07ccde6d6', 'donor', '+977 9800000001', 'Bharatpur, Chitwan'),
('Sample Receiver', 'receiver@example.com', 'pbkdf2:sha256:600000$fcstudent$0e0d9ead5d2d3cae406008d876eae4933d45c83223b43b04eb23d0a07ccde6d6', 'receiver', '+977 9800000002', 'Gaindakot, Nawalpur'),
('System Admin', 'admin@example.com', 'pbkdf2:sha256:600000$fcstudent$0e0d9ead5d2d3cae406008d876eae4933d45c83223b43b04eb23d0a07ccde6d6', 'admin', '+977 9800000003', 'Nawalpur, Nepal');

INSERT INTO donations
(user_id, donation_type, item_name, quantity, size, description, contact_phone, `condition`, pickup_location, status)
VALUES
(1, 'Food', 'Cooked Meals', 25, NULL, 'Fresh meals prepared for a local community group.', '+977 9800000001', 'Fresh', 'Bharatpur, Chitwan', 'Pending'),
(1, 'Clothes', 'Winter Clothes', 12, 'Mixed', 'Clean winter clothes in good condition.', '+977 9800000001', 'Good', 'Bharatpur, Chitwan', 'Approved');

INSERT INTO donation_requests
(user_id, request_type, item_name, quantity, size, reason, address, contact_phone, people_count, description, status)
VALUES
(2, 'Food', 'Rice and Groceries', 20, NULL, 'Support for a family group.', 'Gaindakot, Nawalpur', '+977 9800000002', 6, 'Basic grocery support needed.', 'Pending'),
(2, 'Clothes', 'Children''s Wear', 8, 'Mixed', 'Clothes needed for children.', 'Gaindakot, Nawalpur', '+977 9800000002', NULL, 'School and winter clothes.', 'Approved');

INSERT INTO contact_messages (name, email, subject, message)
VALUES
('Demo Visitor', 'visitor@example.com', 'Partnership Inquiry', 'I would like to know more about partnering with F&C.');

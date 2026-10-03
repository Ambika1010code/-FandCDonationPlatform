CREATE DATABASE IF NOT EXISTS fc_donation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fc_donation;

SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS delivery_tasks;
DROP TABLE IF EXISTS contact_messages;
DROP TABLE IF EXISTS donation_requests;
DROP TABLE IF EXISTS donations;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS=1;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('donor','receiver','admin','volunteer') NOT NULL DEFAULT 'donor',
    phone VARCHAR(30),
    address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE donations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    donation_type VARCHAR(150) NOT NULL,
    item_name VARCHAR(120) NOT NULL,
    quantity INT NOT NULL,
    size VARCHAR(30),
    items_json JSON NULL,
    image_paths JSON NULL,
    description TEXT,
    contact_phone VARCHAR(30),
    `condition` VARCHAR(50),
    pickup_location VARCHAR(255) NOT NULL,
    available_date DATETIME NULL,
    status ENUM('Pending','Approved','Assigned','Picked Up','Delivered','Rejected') NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_donation_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_donation_status(status),
    INDEX idx_donation_user(user_id)
) ENGINE=InnoDB;

CREATE TABLE donation_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    request_type ENUM('Food','Clothes','Accessories') NOT NULL,
    item_name VARCHAR(120) NOT NULL,
    quantity INT NOT NULL,
    size VARCHAR(30),
    `condition` VARCHAR(50),
    reason VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(30),
    people_count INT NULL,
    needed_by DATETIME NULL,
    description TEXT,
    status ENUM('Pending','Approved','Assigned','Picked Up','Delivered','Rejected') NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_request_status(status),
    INDEX idx_request_user(user_id)
) ENGINE=InnoDB;

CREATE TABLE delivery_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_type ENUM('donation','request') NOT NULL,
    item_id INT NOT NULL,
    volunteer_id INT NOT NULL,
    status ENUM('Assigned','Picked Up','Delivered','Cancelled') NOT NULL DEFAULT 'Assigned',
    notes TEXT,
    scheduled_at DATETIME NULL,
    picked_up_at DATETIME NULL,
    delivered_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_delivery_volunteer FOREIGN KEY (volunteer_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_delivery_item(task_type,item_id),
    INDEX idx_delivery_volunteer(volunteer_id),
    INDEX idx_delivery_status(status)
) ENGINE=InnoDB;

CREATE TABLE contact_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(190) NOT NULL,
    subject VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

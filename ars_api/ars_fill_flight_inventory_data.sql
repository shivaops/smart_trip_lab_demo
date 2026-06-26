-- Smart Trip / ARS demo flight inventory reset - DYNAMIC VERSION V4
-- Fixes MySQL Error 1137 Cannot reopen temporary table
-- Cross-validated against flight/fare DDL column types
-- Purpose:
--   Rebuild ARS flight and fare inventory without hard-coded fixed date range.
--   Change only the TOP SETTINGS below.
--
-- Tested purpose:
--   Local Smart Trip demo / ARS provider simulator only.
--
-- IMPORTANT:
--   This script TRUNCATES ARS booking/payment/passenger/itinerary data and rebuilds flight/fare inventory.
--   Run only on your local demo database. Do NOT run on production.

USE `ars`;

-- ============================================================
-- TOP SETTINGS - CHANGE ONLY THESE VALUES WHEN NEEDED
-- ============================================================

-- First departure date to create inventory from:
SET @INV_START_DATE = DATE('2026-06-26');

-- How many calendar days of flight inventory are required?
-- Example:
--   30  = 30 days from start date
--   90  = 90 days from start date
--   180 = 180 days from start date
--   365 = 365 days from start date
SET @INV_DAYS = 60;

-- Starting IDs used for rebuilt demo inventory.
-- Usually no need to change these because tables are truncated before insert.
SET @START_FLIGHT_ID = 100001;
SET @START_FARE_ID   = 200001;

-- Default available seats for every flight.
SET @DEFAULT_AVAILABLE_SEATS = 100;

-- Auto-calculated end date. Do not change.
SET @INV_END_DATE = DATE_ADD(@INV_START_DATE, INTERVAL (@INV_DAYS - 1) DAY);

-- Safety validation.
SET @ERR_MSG = NULL;
SET @ERR_MSG = IF(@INV_START_DATE IS NULL, 'Invalid @INV_START_DATE', @ERR_MSG);
SET @ERR_MSG = IF(@INV_DAYS IS NULL OR @INV_DAYS <= 0, 'Invalid @INV_DAYS. It must be greater than zero.', @ERR_MSG);

-- MySQL SIGNAL cannot be used directly outside stored program in all versions,
-- so the procedure below performs final validation before insert.

SET SQL_SAFE_UPDATES = 0;
SET FOREIGN_KEY_CHECKS = 0;

-- Clean booking/transaction tables first because they can reference flight/fare/passenger data.
TRUNCATE TABLE `upgrade_request`;
TRUNCATE TABLE `itinerary_passenger`;
TRUNCATE TABLE `itinerary`;
TRUNCATE TABLE `payment`;
TRUNCATE TABLE `booking_passenger`;
TRUNCATE TABLE `booking`;
TRUNCATE TABLE `passenger_preferences`;
TRUNCATE TABLE `travel_documents`;
TRUNCATE TABLE `passenger`;

-- Clean and rebuild ARS search inventory.
TRUNCATE TABLE `fare`;
TRUNCATE TABLE `flight`;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- INTERNAL WORK TEMPLATE TABLES
-- These are normal work tables, not TEMPORARY tables, because MySQL can raise Error 1137
-- when the same TEMPORARY table is referenced multiple times inside a stored procedure.
-- These 8 flight templates are copied from the original demo pattern.
-- Each inventory day creates the same 8 demo flights with new dates.
-- ============================================================

DROP TABLE IF EXISTS `_flight_template`;
CREATE TABLE `_flight_template` (
  `route_seq` INT NOT NULL,
  `flight_number` VARCHAR(10) NOT NULL,
  `airline_code` CHAR(2) NOT NULL,
  `departure_airport` CHAR(3) NOT NULL,
  `arrival_airport` CHAR(3) NOT NULL,
  `dep_time` TIME NOT NULL,
  `duration_min` INT NOT NULL,
  `flight_status` ENUM('Scheduled','Delayed','Cancelled','Departed','Arrived') NOT NULL,
  `aircraft_type` VARCHAR(20) NULL,
  `distance_km` INT NULL,
  `from_city` VARCHAR(20) NULL,
  `to_city` VARCHAR(20) NULL,
  `journey_type` ENUM('ONEWAY','ROUNDTRIP_LEG') NOT NULL,
  `marketing_airline_code` CHAR(2) NULL,
  `operating_airline_code` CHAR(2) NULL,
  `no_of_stop` ENUM('0','1','2','3') NULL,
  `layover1_airport_code` CHAR(3) NULL,
  `layover1_min` INT NULL,
  `layover2_airport_code` CHAR(3) NULL,
  `layover2_min` INT NULL,
  `layover3_airport_code` CHAR(3) NULL,
  `layover3_min` INT NULL,
  `terminal_departure` VARCHAR(10) NULL,
  `terminal_arrival` VARCHAR(10) NULL,
  `available_seats` INT NOT NULL,
  `is_active` TINYINT NOT NULL,
  PRIMARY KEY (`route_seq`)
);

INSERT INTO `_flight_template`
(`route_seq`,`flight_number`,`airline_code`,`departure_airport`,`arrival_airport`,`dep_time`,`duration_min`,`flight_status`,`aircraft_type`,`distance_km`,`from_city`,`to_city`,`journey_type`,`marketing_airline_code`,`operating_airline_code`,`no_of_stop`,`layover1_airport_code`,`layover1_min`,`layover2_airport_code`,`layover2_min`,`layover3_airport_code`,`layover3_min`,`terminal_departure`,`terminal_arrival`,`available_seats`,`is_active`)
VALUES
(1,'GF040105','GF','BAH','DOH','06:30:00',60,'Scheduled','A320',150,'Manama','Doha','ONEWAY','GF','GF','0',NULL,NULL,NULL,NULL,NULL,NULL,'T1','T1',9,1),
(2,'QR040106','QR','DOH','BAH','08:10:00',60,'Scheduled','A320',150,'Doha','Manama','ONEWAY','QR','QR','0',NULL,NULL,NULL,NULL,NULL,NULL,'T1','T1',9,1),
(3,'GF040101','GF','BAH','BOM','09:00:00',255,'Scheduled','A320',1950,'Manama','Mumbai','ROUNDTRIP_LEG','GF','GF','0',NULL,NULL,NULL,NULL,NULL,NULL,'T1','T2',9,1),
(4,'AI040104','AI','BOM','BAH','10:15:00',270,'Scheduled','A321',1950,'Mumbai','Manama','ROUNDTRIP_LEG','AI','AI','1','DOH',55,NULL,NULL,NULL,NULL,'T2','T1',9,1),
(5,'QR040102','QR','BAH','BOM','14:30:00',265,'Scheduled','B787',1950,'Manama','Mumbai','ROUNDTRIP_LEG','QR','GF','0',NULL,NULL,NULL,NULL,NULL,NULL,'T1','T2',9,1),
(6,'EK040107','EK','BAH','DXB','16:20:00',80,'Scheduled','B737',490,'Manama','Dubai','ONEWAY','EK','EK','0',NULL,NULL,NULL,NULL,NULL,NULL,'T1','T3',9,1),
(7,'GF040103','GF','BOM','BAH','21:45:00',255,'Scheduled','A320',1950,'Mumbai','Manama','ROUNDTRIP_LEG','GF','GF','0',NULL,NULL,NULL,NULL,NULL,NULL,'T2','T1',9,1),
(8,'EY040108','EY','BAH','DEL','23:10:00',360,'Scheduled','A321',2600,'Manama','Delhi','ROUNDTRIP_LEG','EY','EY','1','DOH',70,NULL,NULL,NULL,NULL,'T1','T3',9,1);

DROP TABLE IF EXISTS `_fare_template`;
CREATE TABLE `_fare_template` (
  `route_seq` INT NOT NULL,
  `global_fare_seq` INT NOT NULL,
  `route_fare_seq` INT NOT NULL,
  `travel_class` ENUM('Economy','Premium Economy','Business','First') NOT NULL,
  `fare_family_code` VARCHAR(20) NULL,
  `fare_family_name` VARCHAR(50) NULL,
  `fare_basis` VARCHAR(15) NOT NULL,
  `refundable` TINYINT NOT NULL,
  `changeable` TINYINT NOT NULL,
  `baggage_allowance` VARCHAR(30) NULL,
  `cabin_baggage` VARCHAR(30) NULL,
  `checkin_baggage` VARCHAR(30) NULL,
  `seat_included` TINYINT NOT NULL,
  `meal_included` TINYINT NOT NULL,
  `priority_included` TINYINT NOT NULL,
  `base_fare` DECIMAL(10,2) NOT NULL,
  `taxes` DECIMAL(10,2) NOT NULL,
  `fees` DECIMAL(10,2) NOT NULL,
  `cancel_penalty` DECIMAL(10,2) NOT NULL,
  `change_penalty` DECIMAL(10,2) NOT NULL,
  `display_rank` INT NOT NULL,
  `is_active` TINYINT NOT NULL,
  `currency` CHAR(3) NOT NULL,
  PRIMARY KEY (`global_fare_seq`)
);

INSERT INTO `_fare_template`
(`route_seq`,`global_fare_seq`,`route_fare_seq`,`travel_class`,`fare_family_code`,`fare_family_name`,`fare_basis`,`refundable`,`changeable`,`baggage_allowance`,`cabin_baggage`,`checkin_baggage`,`seat_included`,`meal_included`,`priority_included`,`base_fare`,`taxes`,`fees`,`cancel_penalty`,`change_penalty`,`display_rank`,`is_active`,`currency`)
VALUES
(1,1,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,16735,4450,450,1500,1000,3,1,'INR'),
(1,2,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,12135,4350,400,4500,2500,2,1,'INR'),
(1,3,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,7935,4200,350,6000,4500,1,1,'INR'),
(1,4,4,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-INR',1,1,'45kg','14kg','45kg',1,1,1,29045,6800,600,1000,750,5,1,'INR'),
(1,5,5,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-INR',1,1,'40kg','12kg','40kg',1,1,1,20545,6500,500,2500,1800,4,1,'INR'),
(1,6,6,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,201.63,53.61,5.42,18.07,12.05,3,1,'USD'),
(1,7,7,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,146.20,52.41,4.82,54.22,30.12,2,1,'USD'),
(1,8,8,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,95.60,50.60,4.22,72.29,54.22,1,1,'USD'),
(1,9,9,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-USD',1,1,'45kg','14kg','45kg',1,1,1,349.94,81.93,7.23,12.05,9.04,5,1,'USD'),
(1,10,10,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-USD',1,1,'40kg','12kg','40kg',1,1,1,247.53,78.31,6.02,30.12,21.69,4,1,'USD'),
(1,11,11,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,349.56,185.02,15.42,264.32,198.24,1,1,'AED'),
(1,12,12,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,534.58,191.63,17.62,198.24,110.13,2,1,'AED'),
(1,13,13,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,737.22,196.04,19.82,66.08,44.05,3,1,'AED'),
(1,14,14,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-AED',1,1,'40kg','12kg','40kg',1,1,1,905.07,286.34,22.03,110.13,79.30,4,1,'AED'),
(1,15,15,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-AED',1,1,'45kg','14kg','45kg',1,1,1,1279.52,299.56,26.43,44.05,33.04,5,1,'AED'),
(1,16,16,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,36.07,19.09,1.59,27.27,20.45,1,1,'BHD'),
(1,17,17,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,55.16,19.77,1.82,20.45,11.36,2,1,'BHD'),
(1,18,18,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,76.07,20.23,2.05,6.82,4.55,3,1,'BHD'),
(1,19,19,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-BHD',1,1,'40kg','12kg','40kg',1,1,1,93.39,29.55,2.27,11.36,8.18,4,1,'BHD'),
(1,20,20,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-BHD',1,1,'45kg','14kg','45kg',1,1,1,132.02,30.91,2.73,4.55,3.41,5,1,'BHD'),
(2,21,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,17535,4450,450,1500,1000,3,1,'INR'),
(2,22,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,12935,4350,400,4500,2500,2,1,'INR'),
(2,23,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,8735,4200,350,6000,4500,1,1,'INR'),
(2,24,4,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-INR',1,1,'45kg','14kg','45kg',1,1,1,30545,6800,600,1000,750,5,1,'INR'),
(2,25,5,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-INR',1,1,'40kg','12kg','40kg',1,1,1,22045,6500,500,2500,1800,4,1,'INR'),
(2,26,6,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,211.27,53.61,5.42,18.07,12.05,3,1,'USD'),
(2,27,7,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,155.84,52.41,4.82,54.22,30.12,2,1,'USD'),
(2,28,8,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,105.24,50.60,4.22,72.29,54.22,1,1,'USD'),
(2,29,9,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-USD',1,1,'45kg','14kg','45kg',1,1,1,368.01,81.93,7.23,12.05,9.04,5,1,'USD'),
(2,30,10,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-USD',1,1,'40kg','12kg','40kg',1,1,1,265.60,78.31,6.02,30.12,21.69,4,1,'USD'),
(2,31,11,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,384.80,185.02,15.42,264.32,198.24,1,1,'AED'),
(2,32,12,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,569.82,191.63,17.62,198.24,110.13,2,1,'AED'),
(2,33,13,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,772.47,196.04,19.82,66.08,44.05,3,1,'AED'),
(2,34,14,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-AED',1,1,'40kg','12kg','40kg',1,1,1,971.15,286.34,22.03,110.13,79.30,4,1,'AED'),
(2,35,15,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-AED',1,1,'45kg','14kg','45kg',1,1,1,1345.59,299.56,26.43,44.05,33.04,5,1,'AED'),
(2,36,16,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,39.70,19.09,1.59,27.27,20.45,1,1,'BHD'),
(2,37,17,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,58.80,19.77,1.82,20.45,11.36,2,1,'BHD'),
(2,38,18,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,79.70,20.23,2.05,6.82,4.55,3,1,'BHD'),
(2,39,19,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-BHD',1,1,'40kg','12kg','40kg',1,1,1,100.20,29.55,2.27,11.36,8.18,4,1,'BHD'),
(2,40,20,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-BHD',1,1,'45kg','14kg','45kg',1,1,1,138.84,30.91,2.73,4.55,3.41,5,1,'BHD'),
(3,41,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,34735,4450,450,1500,1000,3,1,'INR'),
(3,42,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,30135,4350,400,4500,2500,2,1,'INR'),
(3,43,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,25935,4200,350,6000,4500,1,1,'INR'),
(3,44,4,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-INR',1,1,'45kg','14kg','45kg',1,1,1,73045,6800,600,1000,750,5,1,'INR'),
(3,45,5,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-INR',1,1,'40kg','12kg','40kg',1,1,1,64545,6500,500,2500,1800,4,1,'INR'),
(3,46,6,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,418.49,53.61,5.42,18.07,12.05,3,1,'USD'),
(3,47,7,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,363.07,52.41,4.82,54.22,30.12,2,1,'USD'),
(3,48,8,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,312.47,50.60,4.22,72.29,54.22,1,1,'USD'),
(3,49,9,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-USD',1,1,'45kg','14kg','45kg',1,1,1,880.06,81.93,7.23,12.05,9.04,5,1,'USD'),
(3,50,10,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-USD',1,1,'40kg','12kg','40kg',1,1,1,777.65,78.31,6.02,30.12,21.69,4,1,'USD'),
(3,51,11,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,1142.51,185.02,15.42,264.32,198.24,1,1,'AED'),
(3,52,12,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,1327.53,191.63,17.62,198.24,110.13,2,1,'AED'),
(3,53,13,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,1530.18,196.04,19.82,66.08,44.05,3,1,'AED'),
(3,54,14,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-AED',1,1,'40kg','12kg','40kg',1,1,1,2843.39,286.34,22.03,110.13,79.30,4,1,'AED'),
(3,55,15,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-AED',1,1,'45kg','14kg','45kg',1,1,1,3217.84,299.56,26.43,44.05,33.04,5,1,'AED'),
(3,56,16,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,117.89,19.09,1.59,27.27,20.45,1,1,'BHD'),
(3,57,17,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,136.98,19.77,1.82,20.45,11.36,2,1,'BHD'),
(3,58,18,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,157.89,20.23,2.05,6.82,4.55,3,1,'BHD'),
(3,59,19,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-BHD',1,1,'40kg','12kg','40kg',1,1,1,293.39,29.55,2.27,11.36,8.18,4,1,'BHD'),
(3,60,20,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-BHD',1,1,'45kg','14kg','45kg',1,1,1,332.02,30.91,2.73,4.55,3.41,5,1,'BHD'),
(4,61,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,35935,4450,550,1500,1000,3,1,'INR'),
(4,62,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,31335,4350,500,4500,2500,2,1,'INR'),
(4,63,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,27135,4200,450,6000,4500,1,1,'INR'),
(4,64,4,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,432.95,53.61,6.63,18.07,12.05,3,1,'USD'),
(4,65,5,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,377.53,52.41,6.02,54.22,30.12,2,1,'USD'),
(4,66,6,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,326.93,50.60,5.42,72.29,54.22,1,1,'USD'),
(4,67,7,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,1195.37,185.02,19.82,264.32,198.24,1,1,'AED'),
(4,68,8,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,1380.40,191.63,22.03,198.24,110.13,2,1,'AED'),
(4,69,9,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,1583.04,196.04,24.23,66.08,44.05,3,1,'AED'),
(4,70,10,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,123.34,19.09,2.05,27.27,20.45,1,1,'BHD'),
(4,71,11,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,142.43,19.77,2.27,20.45,11.36,2,1,'BHD'),
(4,72,12,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,163.34,20.23,2.50,6.82,4.55,3,1,'BHD'),
(5,73,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,35635,4450,450,1500,1000,3,1,'INR'),
(5,74,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,31035,4350,400,4500,2500,2,1,'INR'),
(5,75,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,26835,4200,350,6000,4500,1,1,'INR'),
(5,76,4,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-INR',1,1,'45kg','14kg','45kg',1,1,1,74745,6800,600,1000,750,5,1,'INR'),
(5,77,5,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-INR',1,1,'40kg','12kg','40kg',1,1,1,66245,6500,500,2500,1800,4,1,'INR'),
(5,78,6,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,429.34,53.61,5.42,18.07,12.05,3,1,'USD'),
(5,79,7,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,373.92,52.41,4.82,54.22,30.12,2,1,'USD'),
(5,80,8,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,323.31,50.60,4.22,72.29,54.22,1,1,'USD'),
(5,81,9,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-USD',1,1,'45kg','14kg','45kg',1,1,1,900.54,81.93,7.23,12.05,9.04,5,1,'USD'),
(5,82,10,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-USD',1,1,'40kg','12kg','40kg',1,1,1,798.13,78.31,6.02,30.12,21.69,4,1,'USD'),
(5,83,11,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,1182.16,185.02,15.42,264.32,198.24,1,1,'AED'),
(5,84,12,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,1367.18,191.63,17.62,198.24,110.13,2,1,'AED'),
(5,85,13,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,1569.82,196.04,19.82,66.08,44.05,3,1,'AED'),
(5,86,14,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-AED',1,1,'40kg','12kg','40kg',1,1,1,2918.28,286.34,22.03,110.13,79.30,4,1,'AED'),
(5,87,15,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-AED',1,1,'45kg','14kg','45kg',1,1,1,3292.73,299.56,26.43,44.05,33.04,5,1,'AED'),
(5,88,16,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,121.98,19.09,1.59,27.27,20.45,1,1,'BHD'),
(5,89,17,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,141.07,19.77,1.82,20.45,11.36,2,1,'BHD'),
(5,90,18,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,161.98,20.23,2.05,6.82,4.55,3,1,'BHD'),
(5,91,19,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-BHD',1,1,'40kg','12kg','40kg',1,1,1,301.11,29.55,2.27,11.36,8.18,4,1,'BHD'),
(5,92,20,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-BHD',1,1,'45kg','14kg','45kg',1,1,1,339.75,30.91,2.73,4.55,3.41,5,1,'BHD'),
(6,93,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,20535,4450,450,1500,1000,3,1,'INR'),
(6,94,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,15935,4350,400,4500,2500,2,1,'INR'),
(6,95,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,11735,4200,350,6000,4500,1,1,'INR'),
(6,96,4,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-INR',1,1,'45kg','14kg','45kg',1,1,1,35045,6800,600,1000,750,5,1,'INR'),
(6,97,5,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-INR',1,1,'40kg','12kg','40kg',1,1,1,26545,6500,500,2500,1800,4,1,'INR'),
(6,98,6,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,247.41,53.61,5.42,18.07,12.05,3,1,'USD'),
(6,99,7,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,191.99,52.41,4.82,54.22,30.12,2,1,'USD'),
(6,100,8,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,141.39,50.60,4.22,72.29,54.22,1,1,'USD'),
(6,101,9,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-USD',1,1,'45kg','14kg','45kg',1,1,1,422.23,81.93,7.23,12.05,9.04,5,1,'USD'),
(6,102,10,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-USD',1,1,'40kg','12kg','40kg',1,1,1,319.82,78.31,6.02,30.12,21.69,4,1,'USD'),
(6,103,11,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,516.96,185.02,15.42,264.32,198.24,1,1,'AED'),
(6,104,12,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,701.98,191.63,17.62,198.24,110.13,2,1,'AED'),
(6,105,13,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,904.63,196.04,19.82,66.08,44.05,3,1,'AED'),
(6,106,14,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-AED',1,1,'40kg','12kg','40kg',1,1,1,1169.38,286.34,22.03,110.13,79.30,4,1,'AED'),
(6,107,15,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-AED',1,1,'45kg','14kg','45kg',1,1,1,1543.83,299.56,26.43,44.05,33.04,5,1,'AED'),
(6,108,16,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,53.34,19.09,1.59,27.27,20.45,1,1,'BHD'),
(6,109,17,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,72.43,19.77,1.82,20.45,11.36,2,1,'BHD'),
(6,110,18,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,93.34,20.23,2.05,6.82,4.55,3,1,'BHD'),
(6,111,19,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-BHD',1,1,'40kg','12kg','40kg',1,1,1,120.66,29.55,2.27,11.36,8.18,4,1,'BHD'),
(6,112,20,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-BHD',1,1,'45kg','14kg','45kg',1,1,1,159.30,30.91,2.73,4.55,3.41,5,1,'BHD'),
(7,113,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,34535,4450,450,1500,1000,3,1,'INR'),
(7,114,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,29935,4350,400,4500,2500,2,1,'INR'),
(7,115,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,25735,4200,350,6000,4500,1,1,'INR'),
(7,116,4,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-INR',1,1,'45kg','14kg','45kg',1,1,1,72545,6800,600,1000,750,5,1,'INR'),
(7,117,5,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-INR',1,1,'40kg','12kg','40kg',1,1,1,64045,6500,500,2500,1800,4,1,'INR'),
(7,118,6,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,416.08,53.61,5.42,18.07,12.05,3,1,'USD'),
(7,119,7,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,360.66,52.41,4.82,54.22,30.12,2,1,'USD'),
(7,120,8,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,310.06,50.60,4.22,72.29,54.22,1,1,'USD'),
(7,121,9,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-USD',1,1,'45kg','14kg','45kg',1,1,1,874.04,81.93,7.23,12.05,9.04,5,1,'USD'),
(7,122,10,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-USD',1,1,'40kg','12kg','40kg',1,1,1,771.63,78.31,6.02,30.12,21.69,4,1,'USD'),
(7,123,11,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,1133.70,185.02,15.42,264.32,198.24,1,1,'AED'),
(7,124,12,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,1318.72,191.63,17.62,198.24,110.13,2,1,'AED'),
(7,125,13,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,1521.37,196.04,19.82,66.08,44.05,3,1,'AED'),
(7,126,14,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-AED',1,1,'40kg','12kg','40kg',1,1,1,2821.37,286.34,22.03,110.13,79.30,4,1,'AED'),
(7,127,15,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-AED',1,1,'45kg','14kg','45kg',1,1,1,3195.81,299.56,26.43,44.05,33.04,5,1,'AED'),
(7,128,16,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,116.98,19.09,1.59,27.27,20.45,1,1,'BHD'),
(7,129,17,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,136.07,19.77,1.82,20.45,11.36,2,1,'BHD'),
(7,130,18,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,156.98,20.23,2.05,6.82,4.55,3,1,'BHD'),
(7,131,19,'Business','BUSINESS_LITE','Business Lite','BUS-LITE-BHD',1,1,'40kg','12kg','40kg',1,1,1,291.11,29.55,2.27,11.36,8.18,4,1,'BHD'),
(7,132,20,'Business','BUSINESS_FLEX','Business Flex','BUS-FLEX-BHD',1,1,'45kg','14kg','45kg',1,1,1,329.75,30.91,2.73,4.55,3.41,5,1,'BHD'),
(8,133,1,'Economy','FLEX','Economy Flex','ECO-FLEX-INR',1,1,'30kg','7kg','30kg',1,1,1,32135,4450,550,1500,1000,3,1,'INR'),
(8,134,2,'Economy','SMART','Economy Smart','ECO-SMART-INR',0,1,'25kg','7kg','25kg',1,1,0,27535,4350,500,4500,2500,2,1,'INR'),
(8,135,3,'Economy','LIGHT','Economy Light','ECO-LIGHT-INR',0,0,'15kg','7kg','15kg',0,0,0,23335,4200,450,6000,4500,1,1,'INR'),
(8,136,4,'Economy','FLEX','Economy Flex','ECO-FLEX-USD',1,1,'30kg','7kg','30kg',1,1,1,387.17,53.61,6.63,18.07,12.05,3,1,'USD'),
(8,137,5,'Economy','SMART','Economy Smart','ECO-SMART-USD',0,1,'25kg','7kg','25kg',1,1,0,331.75,52.41,6.02,54.22,30.12,2,1,'USD'),
(8,138,6,'Economy','LIGHT','Economy Light','ECO-LIGHT-USD',0,0,'15kg','7kg','15kg',0,0,0,281.14,50.60,5.42,72.29,54.22,1,1,'USD'),
(8,139,7,'Economy','LIGHT','Economy Light','ECO-LIGHT-AED',0,0,'15kg','7kg','15kg',0,0,0,1027.97,185.02,19.82,264.32,198.24,1,1,'AED'),
(8,140,8,'Economy','SMART','Economy Smart','ECO-SMART-AED',0,1,'25kg','7kg','25kg',1,1,0,1213,191.63,22.03,198.24,110.13,2,1,'AED'),
(8,141,9,'Economy','FLEX','Economy Flex','ECO-FLEX-AED',1,1,'30kg','7kg','30kg',1,1,1,1415.64,196.04,24.23,66.08,44.05,3,1,'AED'),
(8,142,10,'Economy','LIGHT','Economy Light','ECO-LIGHT-BHD',0,0,'15kg','7kg','15kg',0,0,0,106.07,19.09,2.05,27.27,20.45,1,1,'BHD'),
(8,143,11,'Economy','SMART','Economy Smart','ECO-SMART-BHD',0,1,'25kg','7kg','25kg',1,1,0,125.16,19.77,2.27,20.45,11.36,2,1,'BHD'),
(8,144,12,'Economy','FLEX','Economy Flex','ECO-FLEX-BHD',1,1,'30kg','7kg','30kg',1,1,1,146.07,20.23,2.50,6.82,4.55,3,1,'BHD');

SET @FLIGHTS_PER_DAY = (SELECT COUNT(*) FROM `_flight_template`);
SET @FARES_PER_DAY   = (SELECT COUNT(*) FROM `_fare_template`);

DROP PROCEDURE IF EXISTS `sp_rebuild_ars_demo_inventory_dynamic`;

DELIMITER $$

CREATE PROCEDURE `sp_rebuild_ars_demo_inventory_dynamic`()
BEGIN
  DECLARE v_day INT DEFAULT 0;
  DECLARE v_flight_date DATE;
  DECLARE v_missing INT DEFAULT 0;
  DECLARE v_max_flight_id BIGINT DEFAULT 0;
  DECLARE v_max_fare_id BIGINT DEFAULT 0;

  IF @INV_START_DATE IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid @INV_START_DATE';
  END IF;

  IF @INV_DAYS IS NULL OR @INV_DAYS <= 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid @INV_DAYS. It must be greater than zero.';
  END IF;

  IF @START_FLIGHT_ID IS NULL OR @START_FLIGHT_ID <= 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid @START_FLIGHT_ID. It must be greater than zero.';
  END IF;

  IF @START_FARE_ID IS NULL OR @START_FARE_ID <= 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid @START_FARE_ID. It must be greater than zero.';
  END IF;

  IF @DEFAULT_AVAILABLE_SEATS IS NULL OR @DEFAULT_AVAILABLE_SEATS < 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid @DEFAULT_AVAILABLE_SEATS. It cannot be negative.';
  END IF;

  SET v_max_flight_id = @START_FLIGHT_ID + (@INV_DAYS * @FLIGHTS_PER_DAY) - 1;
  SET v_max_fare_id   = @START_FARE_ID + (@INV_DAYS * @FARES_PER_DAY) - 1;

  IF v_max_flight_id > 2147483647 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Generated flight_id exceeds INT max value. Reduce @INV_DAYS or @START_FLIGHT_ID.';
  END IF;

  IF v_max_fare_id > 2147483647 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Generated fare_id exceeds INT max value. Reduce @INV_DAYS or @START_FARE_ID.';
  END IF;

  SELECT COUNT(*) INTO v_missing
  FROM (
    SELECT `airline_code` AS code FROM `_flight_template`
    UNION
    SELECT `marketing_airline_code` AS code FROM `_flight_template` WHERE `marketing_airline_code` IS NOT NULL
    UNION
    SELECT `operating_airline_code` AS code FROM `_flight_template` WHERE `operating_airline_code` IS NOT NULL
  ) x
  LEFT JOIN `airline` a ON a.`airline_code` = x.code
  WHERE a.`airline_code` IS NULL;

  IF v_missing > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Missing airline master data. Check airline table before loading flights.';
  END IF;

  SELECT COUNT(*) INTO v_missing
  FROM (
    SELECT `departure_airport` AS code FROM `_flight_template`
    UNION
    SELECT `arrival_airport` AS code FROM `_flight_template`
    UNION
    SELECT `layover1_airport_code` AS code FROM `_flight_template` WHERE `layover1_airport_code` IS NOT NULL
    UNION
    SELECT `layover2_airport_code` AS code FROM `_flight_template` WHERE `layover2_airport_code` IS NOT NULL
    UNION
    SELECT `layover3_airport_code` AS code FROM `_flight_template` WHERE `layover3_airport_code` IS NOT NULL
  ) x
  LEFT JOIN `airport` ap ON ap.`airport_code` = x.code
  WHERE ap.`airport_code` IS NULL;

  IF v_missing > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Missing airport master data. Check airport table before loading flights.';
  END IF;

  WHILE v_day < @INV_DAYS DO

    SET v_flight_date = DATE_ADD(@INV_START_DATE, INTERVAL v_day DAY);

    INSERT INTO `flight`
    (`flight_id`, `flight_number`, `airline_code`, `departure_airport`, `arrival_airport`,
     `scheduled_departure`, `scheduled_arrival`, `flight_status`, `aircraft_type`, `distance_km`,
     `duration_min`, `from_city`, `to_city`, `journey_type`, `marketing_airline_code`,
     `operating_airline_code`, `no_of_stop`, `layover1_airport_code`, `layover1_min`,
     `layover2_airport_code`, `layover2_min`, `layover3_airport_code`, `layover3_min`,
     `terminal_departure`, `terminal_arrival`, `available_seats`, `is_active`)
    SELECT
      @START_FLIGHT_ID + (v_day * @FLIGHTS_PER_DAY) + ft.`route_seq` - 1 AS `flight_id`,
      ft.`flight_number`,
      ft.`airline_code`,
      ft.`departure_airport`,
      ft.`arrival_airport`,
      TIMESTAMP(v_flight_date, ft.`dep_time`) AS `scheduled_departure`,
      DATE_ADD(TIMESTAMP(v_flight_date, ft.`dep_time`), INTERVAL ft.`duration_min` MINUTE) AS `scheduled_arrival`,
      ft.`flight_status`,
      ft.`aircraft_type`,
      ft.`distance_km`,
      ft.`duration_min`,
      ft.`from_city`,
      ft.`to_city`,
      ft.`journey_type`,
      ft.`marketing_airline_code`,
      ft.`operating_airline_code`,
      ft.`no_of_stop`,
      ft.`layover1_airport_code`,
      ft.`layover1_min`,
      ft.`layover2_airport_code`,
      ft.`layover2_min`,
      ft.`layover3_airport_code`,
      ft.`layover3_min`,
      ft.`terminal_departure`,
      ft.`terminal_arrival`,
      @DEFAULT_AVAILABLE_SEATS AS `available_seats`,
      ft.`is_active`
    FROM `_flight_template` ft
    ORDER BY ft.`route_seq`;

    INSERT INTO `fare`
    (`fare_id`, `flight_id`, `travel_class`, `fare_family_code`, `fare_family_name`, `fare_basis`,
     `refundable`, `changeable`, `baggage_allowance`, `cabin_baggage`, `checkin_baggage`,
     `seat_included`, `meal_included`, `priority_included`, `base_fare`, `taxes`, `fees`,
     `cancel_penalty`, `change_penalty`, `display_rank`, `is_active`, `currency`)
    SELECT
      @START_FARE_ID + (v_day * @FARES_PER_DAY) + ft.`global_fare_seq` - 1 AS `fare_id`,
      @START_FLIGHT_ID + (v_day * @FLIGHTS_PER_DAY) + ft.`route_seq` - 1 AS `flight_id`,
      ft.`travel_class`,
      ft.`fare_family_code`,
      ft.`fare_family_name`,
      ft.`fare_basis`,
      ft.`refundable`,
      ft.`changeable`,
      ft.`baggage_allowance`,
      ft.`cabin_baggage`,
      ft.`checkin_baggage`,
      ft.`seat_included`,
      ft.`meal_included`,
      ft.`priority_included`,
      ft.`base_fare`,
      ft.`taxes`,
      ft.`fees`,
      ft.`cancel_penalty`,
      ft.`change_penalty`,
      ft.`display_rank`,
      ft.`is_active`,
      ft.`currency`
    FROM `_fare_template` ft
    ORDER BY ft.`global_fare_seq`;

    SET v_day = v_day + 1;

  END WHILE;
END$$

DELIMITER ;

CALL `sp_rebuild_ars_demo_inventory_dynamic`();

DROP PROCEDURE IF EXISTS `sp_rebuild_ars_demo_inventory_dynamic`;

-- Verification summary.
SELECT
  @INV_START_DATE AS inventory_start_date,
  @INV_END_DATE AS inventory_end_date,
  @INV_DAYS AS inventory_days,
  @FLIGHTS_PER_DAY AS flights_per_day,
  @FARES_PER_DAY AS fares_per_day,
  (SELECT COUNT(*) FROM `flight`) AS total_flight_rows,
  (SELECT COUNT(*) FROM `fare`) AS total_fare_rows,
  (SELECT MIN(`scheduled_departure`) FROM `flight`) AS first_departure,
  (SELECT MAX(`scheduled_departure`) FROM `flight`) AS last_departure;

-- Quick check by date.
SELECT
  DATE(`scheduled_departure`) AS flight_date,
  COUNT(*) AS flights
FROM `flight`
GROUP BY DATE(`scheduled_departure`)
ORDER BY flight_date
LIMIT 10;


-- Cleanup internal work template tables after successful run.
DROP TABLE IF EXISTS `_fare_template`;
DROP TABLE IF EXISTS `_flight_template`;

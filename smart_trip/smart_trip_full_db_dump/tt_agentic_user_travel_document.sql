CREATE DATABASE  IF NOT EXISTS `tt_agentic` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `tt_agentic`;
-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: tt_agentic
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `user_travel_document`
--

DROP TABLE IF EXISTS `user_travel_document`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_travel_document` (
  `document_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `traveler_type` enum('Adult','Child','Infant') NOT NULL DEFAULT 'Adult',
  `document_type` enum('Passport','Visa','National ID','Driving License') NOT NULL,
  `document_number` varchar(50) NOT NULL,
  `issuing_country_iso2` char(2) DEFAULT NULL,
  `issue_date` date DEFAULT NULL,
  `expiry_date` date DEFAULT NULL,
  `first_name` varchar(50) DEFAULT NULL,
  `last_name` varchar(50) DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  `gender` enum('Male','Female','Other') DEFAULT NULL,
  `nationality_iso2` char(2) DEFAULT NULL,
  `email` varchar(120) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `phone_iso_code` int DEFAULT NULL,
  `phone_std_code` int DEFAULT NULL,
  `preferred_currency` char(3) NOT NULL DEFAULT 'INR',
  `preferred_language` varchar(10) NOT NULL DEFAULT 'en',
  `seat_preference` enum('Window','Aisle','Any') NOT NULL DEFAULT 'Any',
  `meal_preference` enum('Standard','Vegetarian','Vegan','Halal','Kosher','Diabetic') NOT NULL DEFAULT 'Standard',
  `notify_email` tinyint(1) NOT NULL DEFAULT '1',
  `notify_sms` tinyint(1) NOT NULL DEFAULT '0',
  `is_primary` tinyint(1) NOT NULL DEFAULT '0',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`document_id`),
  UNIQUE KEY `uk1_user_travel_document_user_doc` (`user_id`,`document_number`),
  KEY `ix_user_travel_document_user` (`user_id`),
  KEY `ix_user_travel_document_primary` (`user_id`,`is_primary`,`is_active`),
  KEY `ix_user_travel_document_type` (`user_id`,`traveler_type`,`is_active`),
  CONSTRAINT `fk_user_travel_document_user` FOREIGN KEY (`user_id`) REFERENCES `app_user` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_travel_document`
--

/*!40000 ALTER TABLE `user_travel_document` DISABLE KEYS */;
INSERT INTO `user_travel_document` (`document_id`, `user_id`, `traveler_type`, `document_type`, `document_number`, `issuing_country_iso2`, `issue_date`, `expiry_date`, `first_name`, `last_name`, `date_of_birth`, `gender`, `nationality_iso2`, `email`, `phone`, `phone_iso_code`, `phone_std_code`, `preferred_currency`, `preferred_language`, `seat_preference`, `meal_preference`, `notify_email`, `notify_sms`, `is_primary`, `is_active`, `created_at`, `updated_at`) VALUES (1,1,'Adult','Passport','P1234567','IN','2026-03-02','2036-03-02','Shiva','Naik','1970-03-23','Male','IN','shivanaik@gmail.com','38053730',973,NULL,'INR','en','Window','Standard',1,1,1,1,'2026-03-07 13:20:21','2026-05-11 04:41:23');
INSERT INTO `user_travel_document` (`document_id`, `user_id`, `traveler_type`, `document_type`, `document_number`, `issuing_country_iso2`, `issue_date`, `expiry_date`, `first_name`, `last_name`, `date_of_birth`, `gender`, `nationality_iso2`, `email`, `phone`, `phone_iso_code`, `phone_std_code`, `preferred_currency`, `preferred_language`, `seat_preference`, `meal_preference`, `notify_email`, `notify_sms`, `is_primary`, `is_active`, `created_at`, `updated_at`) VALUES (2,1,'Child','Passport','V123456','IN','2026-03-02','2030-03-01','Vighnesh','Naik','2020-01-04','Male','IN',NULL,NULL,NULL,NULL,'INR','en','Any','Standard',0,0,0,1,'2026-03-07 13:22:57','2026-05-11 12:03:46');
INSERT INTO `user_travel_document` (`document_id`, `user_id`, `traveler_type`, `document_type`, `document_number`, `issuing_country_iso2`, `issue_date`, `expiry_date`, `first_name`, `last_name`, `date_of_birth`, `gender`, `nationality_iso2`, `email`, `phone`, `phone_iso_code`, `phone_std_code`, `preferred_currency`, `preferred_language`, `seat_preference`, `meal_preference`, `notify_email`, `notify_sms`, `is_primary`, `is_active`, `created_at`, `updated_at`) VALUES (3,1,'Infant','Passport','A12345','IN','2026-04-15','2030-06-15','Ishani','Naik','2025-01-01','Female','IN',NULL,NULL,NULL,NULL,'INR','en','Window','Standard',0,0,0,1,'2026-03-07 13:51:31','2026-05-11 09:52:19');
INSERT INTO `user_travel_document` (`document_id`, `user_id`, `traveler_type`, `document_type`, `document_number`, `issuing_country_iso2`, `issue_date`, `expiry_date`, `first_name`, `last_name`, `date_of_birth`, `gender`, `nationality_iso2`, `email`, `phone`, `phone_iso_code`, `phone_std_code`, `preferred_currency`, `preferred_language`, `seat_preference`, `meal_preference`, `notify_email`, `notify_sms`, `is_primary`, `is_active`, `created_at`, `updated_at`) VALUES (5,1,'Adult','Passport','Q124567','IN','2026-03-01','2036-03-01','Shivani','Naik','2014-01-09','Female','IN','shivani@gmail.com','3801234',973,0,'INR','en','Any','Standard',1,0,0,1,'2026-03-09 07:21:02','2026-05-11 04:41:58');
INSERT INTO `user_travel_document` (`document_id`, `user_id`, `traveler_type`, `document_type`, `document_number`, `issuing_country_iso2`, `issue_date`, `expiry_date`, `first_name`, `last_name`, `date_of_birth`, `gender`, `nationality_iso2`, `email`, `phone`, `phone_iso_code`, `phone_std_code`, `preferred_currency`, `preferred_language`, `seat_preference`, `meal_preference`, `notify_email`, `notify_sms`, `is_primary`, `is_active`, `created_at`, `updated_at`) VALUES (9,1,'Adult','Passport','K234567','IN','2026-03-02','2038-03-02','Saraswati','Naik','1990-01-01','Female','IN','saraswati@gmail.com',NULL,NULL,NULL,'INR','en','Any','Standard',0,0,0,1,'2026-04-03 01:31:09','2026-05-11 12:02:19');
/*!40000 ALTER TABLE `user_travel_document` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

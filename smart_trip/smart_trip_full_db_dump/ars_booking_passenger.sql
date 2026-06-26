CREATE DATABASE  IF NOT EXISTS `ars` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `ars`;
-- MySQL dump 10.13  Distrib 8.0.42, for Win64 (x86_64)
--
-- Host: localhost    Database: ars
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
-- Table structure for table `booking_passenger`
--

DROP TABLE IF EXISTS `booking_passenger`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `booking_passenger` (
  `booking_passenger_id` bigint NOT NULL AUTO_INCREMENT,
  `booking_reference` varchar(10) NOT NULL,
  `passenger_id` int NOT NULL,
  `passenger_seq` int NOT NULL,
  `passenger_type` enum('Adult','Child','Infant') NOT NULL,
  `is_lead_passenger` tinyint(1) NOT NULL DEFAULT '0',
  `linked_adult_passenger_id` int DEFAULT NULL,
  `booking_passenger_status` enum('Confirmed','Cancelled','No-Show','Offloaded') NOT NULL DEFAULT 'Confirmed',
  `first_name_snapshot` varchar(50) NOT NULL,
  `last_name_snapshot` varchar(50) NOT NULL,
  `date_of_birth_snapshot` date NOT NULL,
  `gender_snapshot` enum('Male','Female','Other') NOT NULL,
  `nationality_iso2_snapshot` char(2) NOT NULL,
  `document_type_snapshot` enum('Passport','Visa','National ID','Driving License') DEFAULT NULL,
  `document_number_snapshot` varchar(50) DEFAULT NULL,
  `issuing_country_iso2_snapshot` char(2) DEFAULT NULL,
  `document_expiry_snapshot` date DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `base_fare_amount` decimal(12,2) NOT NULL DEFAULT '0.00',
  `tax_amount` decimal(12,2) NOT NULL DEFAULT '0.00',
  `fee_amount` decimal(12,2) NOT NULL DEFAULT '0.00',
  `line_total_amount` decimal(12,2) NOT NULL DEFAULT '0.00',
  PRIMARY KEY (`booking_passenger_id`),
  UNIQUE KEY `uk_booking_passenger_01` (`booking_reference`,`passenger_seq`),
  UNIQUE KEY `uk_booking_passenger_02` (`booking_reference`,`passenger_id`),
  KEY `fk_booking_passenger_02` (`passenger_id`),
  KEY `fk_booking_passenger_03` (`linked_adult_passenger_id`),
  CONSTRAINT `fk_booking_passenger_01` FOREIGN KEY (`booking_reference`) REFERENCES `booking` (`booking_reference`) ON DELETE CASCADE,
  CONSTRAINT `fk_booking_passenger_02` FOREIGN KEY (`passenger_id`) REFERENCES `passenger` (`passenger_id`),
  CONSTRAINT `fk_booking_passenger_03` FOREIGN KEY (`linked_adult_passenger_id`) REFERENCES `passenger` (`passenger_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `booking_passenger`
--

/*!40000 ALTER TABLE `booking_passenger` DISABLE KEYS */;
/*!40000 ALTER TABLE `booking_passenger` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:21

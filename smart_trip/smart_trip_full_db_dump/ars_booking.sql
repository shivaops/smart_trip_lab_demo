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
-- Table structure for table `booking`
--

DROP TABLE IF EXISTS `booking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `booking` (
  `booking_reference` varchar(10) NOT NULL,
  `passenger_id` int NOT NULL,
  `booking_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `booking_status` enum('PENDING','CONFIRMED','FAILED','CANCELLED') NOT NULL,
  `payment_status` enum('PENDING','SUCCESS','FAILED','REFUNDED') DEFAULT 'PENDING',
  `booking_source` enum('Website','Mobile App','Call Center','Travel Agent') DEFAULT 'Website',
  `trip_type` enum('ONE_WAY','ROUND_TRIP','MULTI_CITY') NOT NULL DEFAULT 'ONE_WAY',
  `currency` char(3) NOT NULL DEFAULT 'INR',
  `total_amount` decimal(10,2) NOT NULL DEFAULT '0.00',
  `base_fare_total` decimal(12,2) NOT NULL DEFAULT '0.00',
  `taxes_total` decimal(12,2) NOT NULL DEFAULT '0.00',
  `fees_total` decimal(12,2) NOT NULL DEFAULT '0.00',
  `total_pax_count` int NOT NULL DEFAULT '1',
  `adult_count` int NOT NULL DEFAULT '1',
  `child_count` int NOT NULL DEFAULT '0',
  `infant_count` int NOT NULL DEFAULT '0',
  `pnr_status` enum('Active','Inactive','Archived') NOT NULL DEFAULT 'Active',
  `remarks` varchar(255) DEFAULT NULL,
  `contact_email` varchar(100) DEFAULT NULL,
  `contact_phone` varchar(30) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`booking_reference`),
  KEY `idx_booking_passenger` (`passenger_id`,`booking_date`),
  KEY `idx_booking_status` (`booking_status`,`payment_status`),
  CONSTRAINT `fk_booking_passenger` FOREIGN KEY (`passenger_id`) REFERENCES `passenger` (`passenger_id`) ON DELETE CASCADE,
  CONSTRAINT `ck_booking_01` CHECK ((`total_pax_count` >= 1)),
  CONSTRAINT `ck_booking_02` CHECK (((`adult_count` >= 0) and (`child_count` >= 0) and (`infant_count` >= 0))),
  CONSTRAINT `ck_booking_03` CHECK (((`total_amount` >= 0) and (`base_fare_total` >= 0) and (`taxes_total` >= 0) and (`fees_total` >= 0)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `booking`
--

/*!40000 ALTER TABLE `booking` DISABLE KEYS */;
/*!40000 ALTER TABLE `booking` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

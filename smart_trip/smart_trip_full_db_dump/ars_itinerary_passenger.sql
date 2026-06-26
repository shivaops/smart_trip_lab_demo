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
-- Table structure for table `itinerary_passenger`
--

DROP TABLE IF EXISTS `itinerary_passenger`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `itinerary_passenger` (
  `itinerary_passenger_id` bigint NOT NULL AUTO_INCREMENT,
  `segment_id` int NOT NULL,
  `booking_reference` varchar(10) NOT NULL,
  `booking_passenger_id` bigint NOT NULL,
  `passenger_id` int NOT NULL,
  `seat_assignment` varchar(10) DEFAULT NULL,
  `ticket_number` varchar(30) DEFAULT NULL,
  `coupon_number` int DEFAULT NULL,
  `segment_passenger_status` enum('Confirmed','Cancelled','Waitlisted','Flown','No-Show','Offloaded') NOT NULL DEFAULT 'Confirmed',
  `checkin_status` enum('Not Checked-in','Checked-in','Boarded') NOT NULL DEFAULT 'Not Checked-in',
  `boarding_status` enum('Not Boarded','Boarded') NOT NULL DEFAULT 'Not Boarded',
  `baggage_status` enum('None','Checked-In','Loaded','Delivered') NOT NULL DEFAULT 'None',
  `meal_status` enum('Pending','Loaded','Served','Not Required') NOT NULL DEFAULT 'Pending',
  `meal_code` varchar(20) DEFAULT NULL,
  `ssr_code` varchar(20) DEFAULT NULL,
  `remarks` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`itinerary_passenger_id`),
  UNIQUE KEY `uk_itinerary_passenger_01` (`segment_id`,`booking_passenger_id`),
  UNIQUE KEY `uk_itinerary_passenger_02` (`ticket_number`,`coupon_number`),
  KEY `fk_itinerary_passenger_02` (`booking_reference`),
  KEY `fk_itinerary_passenger_03` (`booking_passenger_id`),
  KEY `fk_itinerary_passenger_04` (`passenger_id`),
  CONSTRAINT `fk_itinerary_passenger_01` FOREIGN KEY (`segment_id`) REFERENCES `itinerary` (`segment_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_itinerary_passenger_02` FOREIGN KEY (`booking_reference`) REFERENCES `booking` (`booking_reference`) ON DELETE CASCADE,
  CONSTRAINT `fk_itinerary_passenger_03` FOREIGN KEY (`booking_passenger_id`) REFERENCES `booking_passenger` (`booking_passenger_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_itinerary_passenger_04` FOREIGN KEY (`passenger_id`) REFERENCES `passenger` (`passenger_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `itinerary_passenger`
--

/*!40000 ALTER TABLE `itinerary_passenger` DISABLE KEYS */;
/*!40000 ALTER TABLE `itinerary_passenger` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:21

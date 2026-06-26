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
-- Table structure for table `itinerary`
--

DROP TABLE IF EXISTS `itinerary`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `itinerary` (
  `segment_id` int NOT NULL AUTO_INCREMENT,
  `booking_reference` varchar(10) NOT NULL,
  `sequence_no` int NOT NULL,
  `flight_id` int NOT NULL,
  `scheduled_departure` datetime DEFAULT NULL,
  `scheduled_arrival` datetime DEFAULT NULL,
  `origin_airport_code` varchar(10) DEFAULT NULL,
  `destination_airport_code` varchar(10) DEFAULT NULL,
  `marketing_airline_code` varchar(10) DEFAULT NULL,
  `operating_airline_code` varchar(10) DEFAULT NULL,
  `flight_number` varchar(20) DEFAULT NULL,
  `segment_status` enum('Confirmed','Cancelled','Flown') DEFAULT 'Confirmed',
  `cabin_class` enum('Economy','Premium Economy','Business','First') NOT NULL,
  `fare_id` int DEFAULT NULL,
  PRIMARY KEY (`segment_id`),
  UNIQUE KEY `uk_booking_sequence` (`booking_reference`,`sequence_no`),
  KEY `fk_itin_fare` (`fare_id`),
  KEY `idx_itin_booking` (`booking_reference`),
  KEY `idx_itin_flight` (`flight_id`),
  CONSTRAINT `fk_itin_booking` FOREIGN KEY (`booking_reference`) REFERENCES `booking` (`booking_reference`) ON DELETE CASCADE,
  CONSTRAINT `fk_itin_fare` FOREIGN KEY (`fare_id`) REFERENCES `fare` (`fare_id`),
  CONSTRAINT `fk_itin_flight` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `itinerary`
--

/*!40000 ALTER TABLE `itinerary` DISABLE KEYS */;
/*!40000 ALTER TABLE `itinerary` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

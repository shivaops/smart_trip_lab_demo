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
-- Table structure for table `api_provider_endpoint`
--

DROP TABLE IF EXISTS `api_provider_endpoint`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_provider_endpoint` (
  `endpoint_id` int NOT NULL AUTO_INCREMENT,
  `provider_code` varchar(30) NOT NULL,
  `endpoint_type` enum('FLIGHT_SEARCH','FLIGHT_BOOK','FLIGHT_PAY','FLIGHT_ITINERARY') NOT NULL,
  `http_method` enum('GET','POST') NOT NULL DEFAULT 'POST',
  `path` varchar(255) NOT NULL,
  `timeout_ms` int NOT NULL DEFAULT '15000',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`endpoint_id`),
  UNIQUE KEY `uk_endpoint_provider_type` (`provider_code`,`endpoint_type`),
  KEY `ix_endpoint_active` (`provider_code`,`is_active`),
  CONSTRAINT `fk_endpoint_provider` FOREIGN KEY (`provider_code`) REFERENCES `api_provider` (`provider_code`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `api_provider_endpoint`
--

/*!40000 ALTER TABLE `api_provider_endpoint` DISABLE KEYS */;
INSERT INTO `api_provider_endpoint` (`endpoint_id`, `provider_code`, `endpoint_type`, `http_method`, `path`, `timeout_ms`, `is_active`, `created_at`) VALUES (1,'ARS_LOCAL','FLIGHT_SEARCH','POST','/v1/flights/search',15000,1,'2026-02-15 17:34:32');
INSERT INTO `api_provider_endpoint` (`endpoint_id`, `provider_code`, `endpoint_type`, `http_method`, `path`, `timeout_ms`, `is_active`, `created_at`) VALUES (2,'ARS_LOCAL','FLIGHT_BOOK','POST','/v1/flights/book',20000,1,'2026-02-15 17:34:32');
INSERT INTO `api_provider_endpoint` (`endpoint_id`, `provider_code`, `endpoint_type`, `http_method`, `path`, `timeout_ms`, `is_active`, `created_at`) VALUES (3,'ARS_LOCAL','FLIGHT_PAY','POST','/v1/flights/pay',20000,1,'2026-02-15 17:34:32');
INSERT INTO `api_provider_endpoint` (`endpoint_id`, `provider_code`, `endpoint_type`, `http_method`, `path`, `timeout_ms`, `is_active`, `created_at`) VALUES (4,'ARS_LOCAL','FLIGHT_ITINERARY','GET','/v1/bookings/{booking_ref}/itinerary',15000,1,'2026-02-23 20:53:56');
/*!40000 ALTER TABLE `api_provider_endpoint` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:23

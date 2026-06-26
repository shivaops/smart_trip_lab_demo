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
-- Table structure for table `agent_payment_txn`
--

DROP TABLE IF EXISTS `agent_payment_txn`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agent_payment_txn` (
  `agent_payment_id` bigint NOT NULL AUTO_INCREMENT,
  `agent_booking_id` bigint NOT NULL,
  `endpoint_id` int NOT NULL,
  `payment_status` enum('PENDING','SUCCESS','FAILED','REFUNDED') NOT NULL,
  `amount` decimal(18,2) DEFAULT NULL,
  `currency` varchar(10) DEFAULT NULL,
  `payment_method` enum('CARD','UPI','WALLET','MOCK_CARD') NOT NULL,
  `payment_ref` varchar(80) DEFAULT NULL,
  `request_json` json DEFAULT NULL,
  `response_json` json DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`agent_payment_id`),
  KEY `ix_pay_booking` (`agent_booking_id`,`created_at`),
  KEY `ix_pay_status` (`payment_status`),
  KEY `ix_pay_ref` (`payment_ref`),
  KEY `fk_pay_endpoint` (`endpoint_id`),
  CONSTRAINT `fk_agent_booking_id` FOREIGN KEY (`agent_booking_id`) REFERENCES `agent_flight_booking` (`agent_booking_id`),
  CONSTRAINT `fk_pay_endpoint` FOREIGN KEY (`endpoint_id`) REFERENCES `api_provider_endpoint` (`endpoint_id`)
) ENGINE=InnoDB AUTO_INCREMENT=211 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `agent_payment_txn`
--

/*!40000 ALTER TABLE `agent_payment_txn` DISABLE KEYS */;
/*!40000 ALTER TABLE `agent_payment_txn` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

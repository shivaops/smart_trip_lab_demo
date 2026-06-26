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
-- Table structure for table `agent_flight_search_result`
--

DROP TABLE IF EXISTS `agent_flight_search_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agent_flight_search_result` (
  `agent_fsr_id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` bigint NOT NULL,
  `endpoint_id` int NOT NULL,
  `selected_flag` tinyint(1) NOT NULL DEFAULT '0',
  `flight_id` int NOT NULL,
  `flight_number` varchar(10) NOT NULL,
  `scheduled_departure` datetime NOT NULL,
  `fare_id` int DEFAULT NULL,
  `request_json` json DEFAULT NULL,
  `response_json` json DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`agent_fsr_id`),
  UNIQUE KEY `uk1_agent_flight_search_result` (`session_id`,`endpoint_id`,`flight_id`,`fare_id`,`flight_number`,`scheduled_departure`),
  KEY `ix_fsr_session_endpoint` (`session_id`,`endpoint_id`),
  KEY `ix_fsr_selected` (`session_id`,`endpoint_id`,`selected_flag`),
  KEY `fk_fsr_endpoint_id` (`endpoint_id`),
  CONSTRAINT `fk_fsr_endpoint_id` FOREIGN KEY (`endpoint_id`) REFERENCES `api_provider_endpoint` (`endpoint_id`),
  CONSTRAINT `fk_fsr_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_session` (`session_id`)
) ENGINE=InnoDB AUTO_INCREMENT=25148 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `agent_flight_search_result`
--

/*!40000 ALTER TABLE `agent_flight_search_result` DISABLE KEYS */;
/*!40000 ALTER TABLE `agent_flight_search_result` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

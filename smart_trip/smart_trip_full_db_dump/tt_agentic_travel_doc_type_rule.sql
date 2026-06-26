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
-- Table structure for table `travel_doc_type_rule`
--

DROP TABLE IF EXISTS `travel_doc_type_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `travel_doc_type_rule` (
  `rule_id` int NOT NULL AUTO_INCREMENT,
  `provider_code` varchar(30) NOT NULL,
  `document_type` varchar(30) NOT NULL,
  `expiry_required` char(1) NOT NULL DEFAULT 'Y',
  `issue_date_required` char(1) NOT NULL DEFAULT 'N',
  `issuing_country_required` char(1) NOT NULL DEFAULT 'Y',
  `name_required` char(1) NOT NULL DEFAULT 'N',
  `is_active` char(1) NOT NULL DEFAULT 'Y',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`),
  UNIQUE KEY `uk1_travel_doc_type_rule` (`provider_code`,`document_type`),
  CONSTRAINT `fk1_travel_doc_type_rule` FOREIGN KEY (`provider_code`) REFERENCES `api_provider` (`provider_code`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `travel_doc_type_rule`
--

/*!40000 ALTER TABLE `travel_doc_type_rule` DISABLE KEYS */;
INSERT INTO `travel_doc_type_rule` (`rule_id`, `provider_code`, `document_type`, `expiry_required`, `issue_date_required`, `issuing_country_required`, `name_required`, `is_active`, `updated_at`) VALUES (1,'ARS_LOCAL','Passport','Y','Y','Y','Y','Y','2026-02-27 19:02:47');
INSERT INTO `travel_doc_type_rule` (`rule_id`, `provider_code`, `document_type`, `expiry_required`, `issue_date_required`, `issuing_country_required`, `name_required`, `is_active`, `updated_at`) VALUES (2,'ARS_LOCAL','Visa','Y','N','Y','N','Y','2026-02-27 19:02:47');
INSERT INTO `travel_doc_type_rule` (`rule_id`, `provider_code`, `document_type`, `expiry_required`, `issue_date_required`, `issuing_country_required`, `name_required`, `is_active`, `updated_at`) VALUES (3,'ARS_LOCAL','National ID','N','N','Y','Y','Y','2026-02-27 19:02:47');
/*!40000 ALTER TABLE `travel_doc_type_rule` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:23

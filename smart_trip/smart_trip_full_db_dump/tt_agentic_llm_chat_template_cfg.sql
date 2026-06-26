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
-- Table structure for table `llm_chat_template_cfg`
--

DROP TABLE IF EXISTS `llm_chat_template_cfg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `llm_chat_template_cfg` (
  `template_id` int NOT NULL AUTO_INCREMENT,
  `template_key` varchar(100) NOT NULL,
  `template_type` enum('SYSTEM','USER','ERROR','HINT','SUMMARY') NOT NULL,
  `template_text` text NOT NULL,
  `is_active` enum('Y','N') NOT NULL DEFAULT 'Y',
  `developer_notes` varchar(1000) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`template_id`),
  UNIQUE KEY `uk1_llm_chat_template_cfg` (`template_key`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `llm_chat_template_cfg`
--

/*!40000 ALTER TABLE `llm_chat_template_cfg` DISABLE KEYS */;
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (1,'INITIAL_WELCOME','SYSTEM','Hello.  Tell me your travel plan in one message, and I will help you step by step.','Y','First system message shown in LLM chat page','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (2,'ASK_MISSING_FIELD','SYSTEM','Please provide {field_label}.','Y','Single missing-field prompt','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (3,'ASK_MISSING_FIELD_WITH_OPTIONS','SYSTEM','Please provide {field_label}. Available options: {options}','Y','Prompt when the field has LOV options','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (4,'INVALID_VALUE_WITH_OPTIONS','ERROR','The value entered for {field_label} is not valid. Please choose one of these: {options}','Y','Prompt for invalid option entry','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (5,'DATE_CLARIFICATION','SYSTEM','I found more than one possible date for {field_label}. Please select one: {options}','Y','Prompt for ambiguous date cases','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (6,'FIELD_UPDATED','SYSTEM','{field_label} updated to {selected_value}.','Y','Acknowledgement after correction/update','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (7,'READY_FOR_SEARCH','SYSTEM','Your request is understood and ready for flight search.','Y','Final ready message before handoff','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (8,'OPTION_REPLY_HINT','HINT','Reply with the option number or exact value.','Y','Hint shown when option selection is expected','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (9,'PROVIDER_UNAVAILABLE','ERROR','Unable to connect to {provider_name}. Please try again later.','Y','LLM/provider connectivity issue','2026-03-31 02:39:26','2026-03-31 10:40:54');
INSERT INTO `llm_chat_template_cfg` (`template_id`, `template_key`, `template_type`, `template_text`, `is_active`, `developer_notes`, `created_at`, `updated_at`) VALUES (10,'SUMMARY_LINE_DEFAULT','SUMMARY','{field_label}: {field_value}','Y','Default summary line renderer','2026-03-31 02:39:26','2026-03-31 10:40:54');
/*!40000 ALTER TABLE `llm_chat_template_cfg` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

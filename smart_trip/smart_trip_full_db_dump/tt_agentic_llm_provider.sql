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
-- Table structure for table `llm_provider`
--

DROP TABLE IF EXISTS `llm_provider`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `llm_provider` (
  `llm_provider_id` int NOT NULL AUTO_INCREMENT,
  `provider_code` varchar(30) NOT NULL,
  `provider_name` varchar(120) NOT NULL,
  `provider_type` enum('CLOUD','LOCAL') NOT NULL,
  `base_url` varchar(255) DEFAULT NULL,
  `auth_type` enum('API_KEY','OAUTH','NONE') NOT NULL DEFAULT 'API_KEY',
  `api_key_env_var` varchar(100) DEFAULT NULL,
  `model_name` varchar(100) NOT NULL,
  `temperature` decimal(3,2) NOT NULL DEFAULT '0.20',
  `max_tokens` int NOT NULL DEFAULT '1024',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `is_default` tinyint(1) NOT NULL DEFAULT '0',
  `notes` varchar(500) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`llm_provider_id`),
  UNIQUE KEY `uk_llm_provider_code_model` (`provider_code`,`model_name`),
  KEY `ix_llm_active` (`is_active`,`is_default`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `llm_provider`
--

/*!40000 ALTER TABLE `llm_provider` DISABLE KEYS */;
INSERT INTO `llm_provider` (`llm_provider_id`, `provider_code`, `provider_name`, `provider_type`, `base_url`, `auth_type`, `api_key_env_var`, `model_name`, `temperature`, `max_tokens`, `is_active`, `is_default`, `notes`, `created_at`) VALUES (1,'GEMINI','Google Gemini 2.5 Flash','CLOUD','https://generativelanguage.googleapis.com','API_KEY','GEMINI_API_KEY','gemini-2.5-flash',0.20,2048,1,0,'Default cloud provider for office environments where local Ollama is unavailable.','2026-03-29 08:05:12');
INSERT INTO `llm_provider` (`llm_provider_id`, `provider_code`, `provider_name`, `provider_type`, `base_url`, `auth_type`, `api_key_env_var`, `model_name`, `temperature`, `max_tokens`, `is_active`, `is_default`, `notes`, `created_at`) VALUES (2,'OLLAMA','Local Ollama Mistral','LOCAL','http://127.0.0.1:11434','NONE',NULL,'mistral',0.20,1024,1,1,'Local fallback/provider for laptop or lab environments with Ollama installed.','2026-03-29 08:05:12');
/*!40000 ALTER TABLE `llm_provider` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

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
-- Table structure for table `api_provider_endpoint_parameter_llm_cfg`
--

DROP TABLE IF EXISTS `api_provider_endpoint_parameter_llm_cfg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_provider_endpoint_parameter_llm_cfg` (
  `llm_cfg_id` int NOT NULL AUTO_INCREMENT,
  `cfg_id` int NOT NULL,
  `is_active` enum('Y','N') NOT NULL DEFAULT 'Y',
  `llm_field_code` varchar(100) NOT NULL,
  `llm_label` varchar(200) DEFAULT NULL,
  `llm_short_label` varchar(100) DEFAULT NULL,
  `ask_in_chat` enum('Y','N') NOT NULL DEFAULT 'Y',
  `show_in_summary_card` enum('Y','N') NOT NULL DEFAULT 'N',
  `show_in_system_card` enum('Y','N') NOT NULL DEFAULT 'N',
  `show_in_user_card` enum('Y','N') NOT NULL DEFAULT 'N',
  `show_in_trace` enum('Y','N') NOT NULL DEFAULT 'Y',
  `input_mode` enum('AUTO','FREE_TEXT','SELECT_ONE','SELECT_MANY','DATE','NUMBER') NOT NULL DEFAULT 'AUTO',
  `correction_mode` enum('NONE','REASK','LOV_PICK','DATE_PICK','STATIC_PICK') NOT NULL DEFAULT 'NONE',
  `option_source_type` enum('NONE','PARENT_CFG_STATIC','PARENT_CFG_SQL','STATIC_LIST','CUSTOM_SQL') NOT NULL DEFAULT 'NONE',
  `option_source_value` text,
  `llm_required_mode` enum('NEVER','ALWAYS','CONDITIONAL') NOT NULL DEFAULT 'NEVER',
  `required_condition_expr` varchar(500) DEFAULT NULL,
  `visibility_condition_expr` varchar(500) DEFAULT NULL,
  `normalization_rule` varchar(200) DEFAULT NULL,
  `parser_hint` varchar(200) DEFAULT NULL,
  `missing_template_key` varchar(100) DEFAULT NULL,
  `invalid_template_key` varchar(100) DEFAULT NULL,
  `selection_template_key` varchar(100) DEFAULT NULL,
  `confirm_template_key` varchar(100) DEFAULT NULL,
  `sort_order` int NOT NULL DEFAULT '10',
  `developer_notes` varchar(1000) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`llm_cfg_id`),
  UNIQUE KEY `uk1_api_provider_endpoint_parameter_llm_cfg` (`cfg_id`),
  KEY `ix1_api_provider_endpoint_parameter_llm_cfg` (`is_active`,`sort_order`),
  KEY `ix2_api_provider_endpoint_parameter_llm_cfg` (`llm_field_code`),
  KEY `ix3_api_provider_endpoint_parameter_llm_cfg` (`missing_template_key`),
  KEY `ix4_api_provider_endpoint_parameter_llm_cfg` (`invalid_template_key`),
  KEY `ix5_api_provider_endpoint_parameter_llm_cfg` (`selection_template_key`),
  KEY `ix6_api_provider_endpoint_parameter_llm_cfg` (`confirm_template_key`),
  CONSTRAINT `fk1_api_provider_endpoint_parameter_llm_cfg` FOREIGN KEY (`cfg_id`) REFERENCES `api_provider_endpoint_parameter_cfg` (`cfg_id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `api_provider_endpoint_parameter_llm_cfg`
--

/*!40000 ALTER TABLE `api_provider_endpoint_parameter_llm_cfg` DISABLE KEYS */;
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (1,87,'Y','trip_type','Trip Type','Trip','Y','Y','Y','Y','Y','SELECT_ONE','LOV_PICK','PARENT_CFG_STATIC',NULL,'ALWAYS',NULL,NULL,'UPPER','ONE_WAY or ROUND_TRIP','ASK_MISSING_FIELD_WITH_OPTIONS','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',10,'LLM chat behavior for existing parent cfg_id 87','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (2,24,'Y','from_airport','From Airport','From','Y','Y','Y','Y','Y','SELECT_ONE','LOV_PICK','PARENT_CFG_SQL',NULL,'ALWAYS',NULL,NULL,'UPPER','Airport code or city/airport name','ASK_MISSING_FIELD','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',20,'LLM origin-airport behavior linked to parent cfg_id 24','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (3,25,'Y','to_airport','To Airport','To','Y','Y','Y','Y','Y','SELECT_ONE','LOV_PICK','PARENT_CFG_SQL',NULL,'ALWAYS',NULL,NULL,'UPPER','Airport code or city/airport name','ASK_MISSING_FIELD','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',30,'LLM destination-airport behavior linked to parent cfg_id 25','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (4,26,'Y','depart_date','Departure Date','Depart','Y','Y','Y','Y','Y','DATE','DATE_PICK','NONE',NULL,'ALWAYS',NULL,NULL,'DATE_ISO','Accept natural language and normalize to YYYY-MM-DD','ASK_MISSING_FIELD','DATE_CLARIFICATION','DATE_CLARIFICATION','FIELD_UPDATED',40,'LLM departure date behavior linked to parent cfg_id 26','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (5,88,'Y','return_date','Return Date','Return','Y','Y','Y','Y','Y','DATE','DATE_PICK','NONE',NULL,'CONDITIONAL','search.trip_type=ROUND_TRIP','search.trip_type=ROUND_TRIP','DATE_ISO','Required only when trip_type is ROUND_TRIP','ASK_MISSING_FIELD','DATE_CLARIFICATION','DATE_CLARIFICATION','FIELD_UPDATED',50,'LLM return-date behavior linked to parent cfg_id 88','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (6,27,'Y','cabin_class','Cabin Class','Cabin','Y','Y','Y','Y','Y','SELECT_ONE','LOV_PICK','PARENT_CFG_STATIC',NULL,'ALWAYS',NULL,NULL,'TITLE_CASE','Economy, Premium Economy, Business, First','ASK_MISSING_FIELD_WITH_OPTIONS','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',60,'LLM cabin behavior linked to parent cfg_id 27','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (7,89,'Y','adults','Adults','Adults','Y','Y','Y','Y','Y','NUMBER','REASK','PARENT_CFG_STATIC',NULL,'ALWAYS',NULL,NULL,'INT','Positive whole number','ASK_MISSING_FIELD','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',70,'LLM adults count behavior linked to parent cfg_id 89','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (8,90,'Y','children','Children','Children','Y','Y','Y','Y','Y','NUMBER','REASK','PARENT_CFG_STATIC',NULL,'NEVER',NULL,NULL,'INT','Optional child count; parent default may still apply later in TT flow','ASK_MISSING_FIELD','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',80,'LLM children count behavior linked to parent cfg_id 90','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (9,91,'Y','infants','Infants','Infants','Y','Y','Y','Y','Y','NUMBER','REASK','PARENT_CFG_STATIC',NULL,'NEVER',NULL,NULL,'INT','Optional infant count; parent default may still apply later in TT flow','ASK_MISSING_FIELD','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',90,'LLM infant count behavior linked to parent cfg_id 91','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (10,28,'Y','preferred_airline','Preferred Airline','Airline','Y','Y','Y','Y','Y','SELECT_ONE','LOV_PICK','PARENT_CFG_SQL',NULL,'NEVER',NULL,NULL,'UPPER','Airline code or airline name','ASK_MISSING_FIELD','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',100,'LLM preferred-airline behavior linked to parent cfg_id 28','2026-03-31 02:39:26','2026-03-31 02:39:26');
INSERT INTO `api_provider_endpoint_parameter_llm_cfg` (`llm_cfg_id`, `cfg_id`, `is_active`, `llm_field_code`, `llm_label`, `llm_short_label`, `ask_in_chat`, `show_in_summary_card`, `show_in_system_card`, `show_in_user_card`, `show_in_trace`, `input_mode`, `correction_mode`, `option_source_type`, `option_source_value`, `llm_required_mode`, `required_condition_expr`, `visibility_condition_expr`, `normalization_rule`, `parser_hint`, `missing_template_key`, `invalid_template_key`, `selection_template_key`, `confirm_template_key`, `sort_order`, `developer_notes`, `created_at`, `updated_at`) VALUES (11,29,'Y','currency','Currency','Currency','Y','Y','Y','Y','Y','SELECT_ONE','LOV_PICK','PARENT_CFG_SQL',NULL,'ALWAYS',NULL,NULL,'UPPER','ISO currency like INR, BHD, USD','ASK_MISSING_FIELD_WITH_OPTIONS','INVALID_VALUE_WITH_OPTIONS','ASK_MISSING_FIELD_WITH_OPTIONS','FIELD_UPDATED',110,'LLM currency behavior linked to parent cfg_id 29','2026-03-31 02:39:26','2026-03-31 02:39:26');
/*!40000 ALTER TABLE `api_provider_endpoint_parameter_llm_cfg` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:23

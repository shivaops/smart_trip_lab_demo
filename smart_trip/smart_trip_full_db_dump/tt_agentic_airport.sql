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
-- Table structure for table `airport`
--

DROP TABLE IF EXISTS `airport`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `airport` (
  `airport_code` char(3) NOT NULL,
  `airport_name` varchar(100) NOT NULL,
  `city_name` varchar(80) NOT NULL,
  `country_iso2` char(2) NOT NULL,
  `timezone` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `display_rank` int NOT NULL DEFAULT '1',
  `airport_city_display` varchar(150) GENERATED ALWAYS AS (concat(`airport_code`,_utf8mb4' - ',`city_name`,_utf8mb4' - ',`airport_name`)) STORED,
  PRIMARY KEY (`airport_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `airport`
--

/*!40000 ALTER TABLE `airport` DISABLE KEYS */;
INSERT INTO `airport` (`airport_code`, `airport_name`, `city_name`, `country_iso2`, `timezone`, `is_active`, `display_rank`) VALUES ('BAH','Bahrain International Airport','Manama','BH','Asia/Bahrain',1,1);
INSERT INTO `airport` (`airport_code`, `airport_name`, `city_name`, `country_iso2`, `timezone`, `is_active`, `display_rank`) VALUES ('BOM','Chhatrapati Shivaji Maharaj International Airport','Mumbai','IN','Asia/Kolkata',1,2);
INSERT INTO `airport` (`airport_code`, `airport_name`, `city_name`, `country_iso2`, `timezone`, `is_active`, `display_rank`) VALUES ('DEL','Indira Gandhi International Airport','Delhi','IN','Asia/Kolkata',1,5);
INSERT INTO `airport` (`airport_code`, `airport_name`, `city_name`, `country_iso2`, `timezone`, `is_active`, `display_rank`) VALUES ('DOH','Hamad International Airport','Doha','QA','Asia/Qatar',1,3);
INSERT INTO `airport` (`airport_code`, `airport_name`, `city_name`, `country_iso2`, `timezone`, `is_active`, `display_rank`) VALUES ('DXB','Dubai International Airport','Dubai','AE','Asia/Dubai',1,4);
/*!40000 ALTER TABLE `airport` ENABLE KEYS */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:23

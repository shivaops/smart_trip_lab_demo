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
-- Temporary view structure for view `vw_passenger_profile`
--

DROP TABLE IF EXISTS `vw_passenger_profile`;
/*!50001 DROP VIEW IF EXISTS `vw_passenger_profile`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_passenger_profile` AS SELECT 
 1 AS `passenger_id`,
 1 AS `passenger_uuid`,
 1 AS `first_name`,
 1 AS `last_name`,
 1 AS `date_of_birth`,
 1 AS `gender`,
 1 AS `nationality_iso2`,
 1 AS `email`,
 1 AS `phone`,
 1 AS `created_at`,
 1 AS `updated_at`,
 1 AS `seat_preference`,
 1 AS `meal_preference`,
 1 AS `language_preference`,
 1 AS `document_id`,
 1 AS `document_type`,
 1 AS `document_number`,
 1 AS `issuing_country_iso2`,
 1 AS `document_expiry_date`,
 1 AS `verification_status`,
 1 AS `scanned_copy_path`,
 1 AS `document_created_at`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `vw_flight_search_api`
--

DROP TABLE IF EXISTS `vw_flight_search_api`;
/*!50001 DROP VIEW IF EXISTS `vw_flight_search_api`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_flight_search_api` AS SELECT 
 1 AS `flight_id`,
 1 AS `flight_number`,
 1 AS `airline_code`,
 1 AS `airline_name`,
 1 AS `from_city`,
 1 AS `to_city`,
 1 AS `departure_airport`,
 1 AS `arrival_airport`,
 1 AS `scheduled_departure`,
 1 AS `scheduled_arrival`,
 1 AS `flight_status`,
 1 AS `aircraft_type`,
 1 AS `distance_km`,
 1 AS `duration_min`,
 1 AS `no_of_stop`,
 1 AS `layover1_airport_code`,
 1 AS `layover1_min`,
 1 AS `layover2_airport_code`,
 1 AS `layover2_min`,
 1 AS `layover3_airport_code`,
 1 AS `layover3_min`,
 1 AS `fare_id`,
 1 AS `travel_class`,
 1 AS `fare_family_code`,
 1 AS `fare_family_name`,
 1 AS `fare_basis`,
 1 AS `refundable`,
 1 AS `changeable`,
 1 AS `baggage_allowance`,
 1 AS `cabin_baggage`,
 1 AS `checkin_baggage`,
 1 AS `seat_included`,
 1 AS `meal_included`,
 1 AS `priority_included`,
 1 AS `cancel_penalty`,
 1 AS `change_penalty`,
 1 AS `display_rank`,
 1 AS `fare_is_active`,
 1 AS `base_fare`,
 1 AS `taxes`,
 1 AS `fees`,
 1 AS `currency`,
 1 AS `scheduled_departure_formatted`,
 1 AS `scheduled_arrival_formatted`,
 1 AS `duration_formatted`,
 1 AS `stops_formatted`,
 1 AS `refundable_formatted`,
 1 AS `changeable_formatted`,
 1 AS `total_fare_calc`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `vw_pnr_summary`
--

DROP TABLE IF EXISTS `vw_pnr_summary`;
/*!50001 DROP VIEW IF EXISTS `vw_pnr_summary`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_pnr_summary` AS SELECT 
 1 AS `booking_reference`,
 1 AS `passenger_name`,
 1 AS `booking_status`,
 1 AS `payment_status`,
 1 AS `booking_total_amount`,
 1 AS `sequence_no`,
 1 AS `flight_number`,
 1 AS `airline_name`,
 1 AS `dep_airport_code`,
 1 AS `arr_airport_code`,
 1 AS `scheduled_departure`,
 1 AS `scheduled_arrival`,
 1 AS `cabin_class`,
 1 AS `fare_total_calc`,
 1 AS `fare_currency`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `vw_payment_full`
--

DROP TABLE IF EXISTS `vw_payment_full`;
/*!50001 DROP VIEW IF EXISTS `vw_payment_full`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_payment_full` AS SELECT 
 1 AS `payment_id`,
 1 AS `booking_reference`,
 1 AS `payment_method`,
 1 AS `payment_status`,
 1 AS `amount`,
 1 AS `currency`,
 1 AS `transaction_id`,
 1 AS `payment_date`,
 1 AS `passenger_id`,
 1 AS `booking_date`,
 1 AS `booking_status`,
 1 AS `booking_payment_status`,
 1 AS `booking_source`,
 1 AS `booking_currency`,
 1 AS `booking_total_amount`,
 1 AS `passenger_uuid`,
 1 AS `first_name`,
 1 AS `last_name`,
 1 AS `email`,
 1 AS `phone`,
 1 AS `nationality_iso2`,
 1 AS `date_of_birth`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `vw_payment_details`
--

DROP TABLE IF EXISTS `vw_payment_details`;
/*!50001 DROP VIEW IF EXISTS `vw_payment_details`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_payment_details` AS SELECT 
 1 AS `payment_id`,
 1 AS `booking_reference`,
 1 AS `payment_method`,
 1 AS `payment_status`,
 1 AS `amount`,
 1 AS `currency`,
 1 AS `transaction_id`,
 1 AS `payment_date`,
 1 AS `passenger_id`,
 1 AS `booking_date`,
 1 AS `booking_status`,
 1 AS `booking_payment_status`,
 1 AS `booking_source`,
 1 AS `booking_currency`,
 1 AS `booking_total_amount`,
 1 AS `passenger_uuid`,
 1 AS `first_name`,
 1 AS `last_name`,
 1 AS `email`,
 1 AS `phone`,
 1 AS `nationality_iso2`,
 1 AS `date_of_birth`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `vw_itinerary_passenger_details`
--

DROP TABLE IF EXISTS `vw_itinerary_passenger_details`;
/*!50001 DROP VIEW IF EXISTS `vw_itinerary_passenger_details`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_itinerary_passenger_details` AS SELECT 
 1 AS `booking_reference`,
 1 AS `booking_date`,
 1 AS `booking_status`,
 1 AS `booking_payment_status`,
 1 AS `booking_source`,
 1 AS `trip_type`,
 1 AS `booking_currency`,
 1 AS `booking_total_amount`,
 1 AS `booking_base_fare_total`,
 1 AS `booking_taxes_total`,
 1 AS `booking_fees_total`,
 1 AS `total_pax_count`,
 1 AS `adult_count`,
 1 AS `child_count`,
 1 AS `infant_count`,
 1 AS `pnr_status`,
 1 AS `booking_contact_email`,
 1 AS `booking_contact_phone`,
 1 AS `booking_remarks`,
 1 AS `booking_created_at`,
 1 AS `booking_updated_at`,
 1 AS `payment_id`,
 1 AS `payment_method`,
 1 AS `payment_status`,
 1 AS `payment_amount`,
 1 AS `payment_currency`,
 1 AS `transaction_id`,
 1 AS `payment_date`,
 1 AS `segment_id`,
 1 AS `sequence_no`,
 1 AS `flight_id`,
 1 AS `scheduled_departure`,
 1 AS `scheduled_arrival`,
 1 AS `origin_airport_code`,
 1 AS `destination_airport_code`,
 1 AS `marketing_airline_code`,
 1 AS `operating_airline_code`,
 1 AS `flight_number`,
 1 AS `segment_status`,
 1 AS `cabin_class`,
 1 AS `fare_id`,
 1 AS `flight_status`,
 1 AS `aircraft_type`,
 1 AS `distance_km`,
 1 AS `duration_min`,
 1 AS `no_of_stop`,
 1 AS `layover1_airport_code`,
 1 AS `layover1_min`,
 1 AS `layover2_airport_code`,
 1 AS `layover2_min`,
 1 AS `layover3_airport_code`,
 1 AS `layover3_min`,
 1 AS `terminal_departure`,
 1 AS `terminal_arrival`,
 1 AS `airline_code`,
 1 AS `airline_name`,
 1 AS `dep_airport_code`,
 1 AS `dep_airport_name`,
 1 AS `dep_city`,
 1 AS `dep_country_iso2`,
 1 AS `dep_timezone`,
 1 AS `dep_airport_display`,
 1 AS `arr_airport_code`,
 1 AS `arr_airport_name`,
 1 AS `arr_city`,
 1 AS `arr_country_iso2`,
 1 AS `arr_timezone`,
 1 AS `arr_airport_display`,
 1 AS `fare_travel_class`,
 1 AS `fare_family_code`,
 1 AS `fare_family_name`,
 1 AS `fare_basis`,
 1 AS `refundable`,
 1 AS `changeable`,
 1 AS `baggage_allowance`,
 1 AS `cabin_baggage`,
 1 AS `checkin_baggage`,
 1 AS `seat_included`,
 1 AS `meal_included`,
 1 AS `priority_included`,
 1 AS `cancel_penalty`,
 1 AS `change_penalty`,
 1 AS `fare_display_rank`,
 1 AS `fare_base_fare`,
 1 AS `fare_taxes`,
 1 AS `fare_fees`,
 1 AS `fare_total_calc`,
 1 AS `fare_currency`,
 1 AS `booking_passenger_id`,
 1 AS `passenger_id`,
 1 AS `passenger_seq`,
 1 AS `passenger_type`,
 1 AS `is_lead_passenger`,
 1 AS `linked_adult_passenger_id`,
 1 AS `booking_passenger_status`,
 1 AS `first_name_snapshot`,
 1 AS `last_name_snapshot`,
 1 AS `passenger_name`,
 1 AS `date_of_birth_snapshot`,
 1 AS `gender_snapshot`,
 1 AS `nationality_iso2_snapshot`,
 1 AS `document_type_snapshot`,
 1 AS `document_number_snapshot`,
 1 AS `issuing_country_iso2_snapshot`,
 1 AS `document_expiry_snapshot`,
 1 AS `pax_base_fare_amount`,
 1 AS `pax_tax_amount`,
 1 AS `pax_fee_amount`,
 1 AS `pax_line_total_amount`,
 1 AS `booking_passenger_created_at`,
 1 AS `booking_passenger_updated_at`,
 1 AS `passenger_uuid`,
 1 AS `passenger_first_name_master`,
 1 AS `passenger_last_name_master`,
 1 AS `passenger_email`,
 1 AS `passenger_phone`,
 1 AS `itinerary_passenger_id`,
 1 AS `seat_assignment`,
 1 AS `ticket_number`,
 1 AS `coupon_number`,
 1 AS `segment_passenger_status`,
 1 AS `checkin_status`,
 1 AS `boarding_status`,
 1 AS `baggage_status`,
 1 AS `meal_status`,
 1 AS `meal_code`,
 1 AS `ssr_code`,
 1 AS `itinerary_passenger_remarks`,
 1 AS `itinerary_passenger_created_at`,
 1 AS `itinerary_passenger_updated_at`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `vw_itinerary_details`
--

DROP TABLE IF EXISTS `vw_itinerary_details`;
/*!50001 DROP VIEW IF EXISTS `vw_itinerary_details`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_itinerary_details` AS SELECT 
 1 AS `booking_reference`,
 1 AS `passenger_id`,
 1 AS `passenger_uuid`,
 1 AS `passenger_name`,
 1 AS `passenger_email`,
 1 AS `passenger_phone`,
 1 AS `booking_date`,
 1 AS `booking_status`,
 1 AS `payment_status`,
 1 AS `booking_source`,
 1 AS `booking_currency`,
 1 AS `booking_total_amount`,
 1 AS `segment_id`,
 1 AS `sequence_no`,
 1 AS `cabin_class`,
 1 AS `flight_id`,
 1 AS `flight_number`,
 1 AS `flight_status`,
 1 AS `aircraft_type`,
 1 AS `distance_km`,
 1 AS `duration_min`,
 1 AS `scheduled_departure`,
 1 AS `scheduled_arrival`,
 1 AS `airline_code`,
 1 AS `airline_name`,
 1 AS `dep_airport_code`,
 1 AS `dep_airport_name`,
 1 AS `dep_city`,
 1 AS `dep_country_iso2`,
 1 AS `dep_timezone`,
 1 AS `arr_airport_code`,
 1 AS `arr_airport_name`,
 1 AS `arr_city`,
 1 AS `arr_country_iso2`,
 1 AS `arr_timezone`,
 1 AS `fare_id`,
 1 AS `fare_travel_class`,
 1 AS `fare_family_code`,
 1 AS `fare_family_name`,
 1 AS `fare_basis`,
 1 AS `refundable`,
 1 AS `changeable`,
 1 AS `baggage_allowance`,
 1 AS `cabin_baggage`,
 1 AS `checkin_baggage`,
 1 AS `seat_included`,
 1 AS `meal_included`,
 1 AS `priority_included`,
 1 AS `cancel_penalty`,
 1 AS `change_penalty`,
 1 AS `display_rank`,
 1 AS `base_fare`,
 1 AS `taxes`,
 1 AS `fees`,
 1 AS `fare_total_calc`,
 1 AS `fare_currency`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `vw_passenger_full`
--

DROP TABLE IF EXISTS `vw_passenger_full`;
/*!50001 DROP VIEW IF EXISTS `vw_passenger_full`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vw_passenger_full` AS SELECT 
 1 AS `passenger_id`,
 1 AS `passenger_uuid`,
 1 AS `first_name`,
 1 AS `last_name`,
 1 AS `date_of_birth`,
 1 AS `gender`,
 1 AS `nationality_iso2`,
 1 AS `email`,
 1 AS `phone`,
 1 AS `created_at`,
 1 AS `updated_at`,
 1 AS `seat_preference`,
 1 AS `meal_preference`,
 1 AS `language_preference`,
 1 AS `passport_document_id`,
 1 AS `passport_number`,
 1 AS `passport_issuing_country`,
 1 AS `passport_expiry_date`,
 1 AS `passport_verification_status`,
 1 AS `passport_scanned_copy_path`,
 1 AS `visa_document_id`,
 1 AS `visa_number`,
 1 AS `visa_issuing_country`,
 1 AS `visa_expiry_date`,
 1 AS `visa_verification_status`,
 1 AS `visa_scanned_copy_path`*/;
SET character_set_client = @saved_cs_client;

--
-- Final view structure for view `vw_passenger_profile`
--

/*!50001 DROP VIEW IF EXISTS `vw_passenger_profile`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_passenger_profile` AS select `p`.`passenger_id` AS `passenger_id`,`p`.`passenger_uuid` AS `passenger_uuid`,`p`.`first_name` AS `first_name`,`p`.`last_name` AS `last_name`,`p`.`date_of_birth` AS `date_of_birth`,`p`.`gender` AS `gender`,`p`.`nationality_iso2` AS `nationality_iso2`,`p`.`email` AS `email`,`p`.`phone` AS `phone`,`p`.`created_at` AS `created_at`,`p`.`updated_at` AS `updated_at`,`pp`.`seat_preference` AS `seat_preference`,`pp`.`meal_preference` AS `meal_preference`,`pp`.`language_preference` AS `language_preference`,`d`.`document_id` AS `document_id`,`d`.`document_type` AS `document_type`,`d`.`document_number` AS `document_number`,`d`.`issuing_country_iso2` AS `issuing_country_iso2`,`d`.`expiry_date` AS `document_expiry_date`,`d`.`verification_status` AS `verification_status`,`d`.`scanned_copy_path` AS `scanned_copy_path`,`d`.`created_at` AS `document_created_at` from ((`passenger` `p` left join `passenger_preferences` `pp` on((`pp`.`passenger_id` = `p`.`passenger_id`))) left join `travel_documents` `d` on((`d`.`passenger_id` = `p`.`passenger_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `vw_flight_search_api`
--

/*!50001 DROP VIEW IF EXISTS `vw_flight_search_api`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_flight_search_api` AS select `f`.`flight_id` AS `flight_id`,`f`.`flight_number` AS `flight_number`,`a`.`airline_code` AS `airline_code`,`a`.`airline_name` AS `airline_name`,`f`.`from_city` AS `from_city`,`f`.`to_city` AS `to_city`,`f`.`departure_airport` AS `departure_airport`,`f`.`arrival_airport` AS `arrival_airport`,`f`.`scheduled_departure` AS `scheduled_departure`,`f`.`scheduled_arrival` AS `scheduled_arrival`,`f`.`flight_status` AS `flight_status`,`f`.`aircraft_type` AS `aircraft_type`,`f`.`distance_km` AS `distance_km`,`f`.`duration_min` AS `duration_min`,`f`.`no_of_stop` AS `no_of_stop`,`f`.`layover1_airport_code` AS `layover1_airport_code`,`f`.`layover1_min` AS `layover1_min`,`f`.`layover2_airport_code` AS `layover2_airport_code`,`f`.`layover2_min` AS `layover2_min`,`f`.`layover3_airport_code` AS `layover3_airport_code`,`f`.`layover3_min` AS `layover3_min`,`fa`.`fare_id` AS `fare_id`,`fa`.`travel_class` AS `travel_class`,`fa`.`fare_family_code` AS `fare_family_code`,`fa`.`fare_family_name` AS `fare_family_name`,`fa`.`fare_basis` AS `fare_basis`,`fa`.`refundable` AS `refundable`,`fa`.`changeable` AS `changeable`,`fa`.`baggage_allowance` AS `baggage_allowance`,`fa`.`cabin_baggage` AS `cabin_baggage`,`fa`.`checkin_baggage` AS `checkin_baggage`,`fa`.`seat_included` AS `seat_included`,`fa`.`meal_included` AS `meal_included`,`fa`.`priority_included` AS `priority_included`,`fa`.`cancel_penalty` AS `cancel_penalty`,`fa`.`change_penalty` AS `change_penalty`,`fa`.`display_rank` AS `display_rank`,`fa`.`is_active` AS `fare_is_active`,`fa`.`base_fare` AS `base_fare`,coalesce(`fa`.`taxes`,0.00) AS `taxes`,coalesce(`fa`.`fees`,0.00) AS `fees`,`fa`.`currency` AS `currency`,date_format(`f`.`scheduled_departure`,'%Y-%m-%d %H:%i') AS `scheduled_departure_formatted`,date_format(`f`.`scheduled_arrival`,'%Y-%m-%d %H:%i') AS `scheduled_arrival_formatted`,(case when (`f`.`duration_min` is null) then NULL else date_format(sec_to_time((`f`.`duration_min` * 60)),'%H:%i') end) AS `duration_formatted`,(case when (`f`.`no_of_stop` is null) then NULL when (`f`.`no_of_stop` = '0') then 'NON-STOP' when (`f`.`no_of_stop` = '1') then '1 STOP' else concat(`f`.`no_of_stop`,' STOPS') end) AS `stops_formatted`,(case when (`fa`.`refundable` = 1) then 'Y' else 'N' end) AS `refundable_formatted`,(case when (`fa`.`changeable` = 1) then 'Y' else 'N' end) AS `changeable_formatted`,((coalesce(`fa`.`base_fare`,0.00) + coalesce(`fa`.`taxes`,0.00)) + coalesce(`fa`.`fees`,0.00)) AS `total_fare_calc` from ((`flight` `f` join `airline` `a` on((`a`.`airline_code` = `f`.`airline_code`))) left join `fare` `fa` on((`fa`.`flight_id` = `f`.`flight_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `vw_pnr_summary`
--

/*!50001 DROP VIEW IF EXISTS `vw_pnr_summary`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_pnr_summary` AS select `it`.`booking_reference` AS `booking_reference`,`it`.`passenger_name` AS `passenger_name`,`it`.`booking_status` AS `booking_status`,`it`.`payment_status` AS `payment_status`,`it`.`booking_total_amount` AS `booking_total_amount`,`it`.`sequence_no` AS `sequence_no`,`it`.`flight_number` AS `flight_number`,`it`.`airline_name` AS `airline_name`,`it`.`dep_airport_code` AS `dep_airport_code`,`it`.`arr_airport_code` AS `arr_airport_code`,`it`.`scheduled_departure` AS `scheduled_departure`,`it`.`scheduled_arrival` AS `scheduled_arrival`,`it`.`cabin_class` AS `cabin_class`,`it`.`fare_total_calc` AS `fare_total_calc`,`it`.`fare_currency` AS `fare_currency` from `vw_itinerary_details` `it` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `vw_payment_full`
--

/*!50001 DROP VIEW IF EXISTS `vw_payment_full`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_payment_full` AS select `pay`.`payment_id` AS `payment_id`,`pay`.`booking_reference` AS `booking_reference`,`pay`.`payment_method` AS `payment_method`,`pay`.`payment_status` AS `payment_status`,`pay`.`amount` AS `amount`,`pay`.`currency` AS `currency`,`pay`.`transaction_id` AS `transaction_id`,`pay`.`payment_date` AS `payment_date`,`b`.`passenger_id` AS `passenger_id`,`b`.`booking_date` AS `booking_date`,`b`.`booking_status` AS `booking_status`,`b`.`payment_status` AS `booking_payment_status`,`b`.`booking_source` AS `booking_source`,`b`.`currency` AS `booking_currency`,`b`.`total_amount` AS `booking_total_amount`,`p`.`passenger_uuid` AS `passenger_uuid`,`p`.`first_name` AS `first_name`,`p`.`last_name` AS `last_name`,`p`.`email` AS `email`,`p`.`phone` AS `phone`,`p`.`nationality_iso2` AS `nationality_iso2`,`p`.`date_of_birth` AS `date_of_birth` from ((`payment` `pay` join `booking` `b` on((`b`.`booking_reference` = `pay`.`booking_reference`))) join `passenger` `p` on((`p`.`passenger_id` = `b`.`passenger_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `vw_payment_details`
--

/*!50001 DROP VIEW IF EXISTS `vw_payment_details`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_payment_details` AS select `pay`.`payment_id` AS `payment_id`,`pay`.`booking_reference` AS `booking_reference`,`pay`.`payment_method` AS `payment_method`,`pay`.`payment_status` AS `payment_status`,`pay`.`amount` AS `amount`,`pay`.`currency` AS `currency`,`pay`.`transaction_id` AS `transaction_id`,`pay`.`payment_date` AS `payment_date`,`b`.`passenger_id` AS `passenger_id`,`b`.`booking_date` AS `booking_date`,`b`.`booking_status` AS `booking_status`,`b`.`payment_status` AS `booking_payment_status`,`b`.`booking_source` AS `booking_source`,`b`.`currency` AS `booking_currency`,`b`.`total_amount` AS `booking_total_amount`,`p`.`passenger_uuid` AS `passenger_uuid`,`p`.`first_name` AS `first_name`,`p`.`last_name` AS `last_name`,`p`.`email` AS `email`,`p`.`phone` AS `phone`,`p`.`nationality_iso2` AS `nationality_iso2`,`p`.`date_of_birth` AS `date_of_birth` from ((`payment` `pay` join `booking` `b` on((`b`.`booking_reference` = `pay`.`booking_reference`))) join `passenger` `p` on((`p`.`passenger_id` = `b`.`passenger_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `vw_itinerary_passenger_details`
--

/*!50001 DROP VIEW IF EXISTS `vw_itinerary_passenger_details`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_itinerary_passenger_details` AS select `b`.`booking_reference` AS `booking_reference`,`b`.`booking_date` AS `booking_date`,`b`.`booking_status` AS `booking_status`,`b`.`payment_status` AS `booking_payment_status`,`b`.`booking_source` AS `booking_source`,`b`.`trip_type` AS `trip_type`,`b`.`currency` AS `booking_currency`,`b`.`total_amount` AS `booking_total_amount`,`b`.`base_fare_total` AS `booking_base_fare_total`,`b`.`taxes_total` AS `booking_taxes_total`,`b`.`fees_total` AS `booking_fees_total`,`b`.`total_pax_count` AS `total_pax_count`,`b`.`adult_count` AS `adult_count`,`b`.`child_count` AS `child_count`,`b`.`infant_count` AS `infant_count`,`b`.`pnr_status` AS `pnr_status`,`b`.`contact_email` AS `booking_contact_email`,`b`.`contact_phone` AS `booking_contact_phone`,`b`.`remarks` AS `booking_remarks`,`b`.`created_at` AS `booking_created_at`,`b`.`updated_at` AS `booking_updated_at`,`pay`.`payment_id` AS `payment_id`,`pay`.`payment_method` AS `payment_method`,`pay`.`payment_status` AS `payment_status`,`pay`.`amount` AS `payment_amount`,`pay`.`currency` AS `payment_currency`,`pay`.`transaction_id` AS `transaction_id`,`pay`.`payment_date` AS `payment_date`,`i`.`segment_id` AS `segment_id`,`i`.`sequence_no` AS `sequence_no`,`i`.`flight_id` AS `flight_id`,`i`.`scheduled_departure` AS `scheduled_departure`,`i`.`scheduled_arrival` AS `scheduled_arrival`,`i`.`origin_airport_code` AS `origin_airport_code`,`i`.`destination_airport_code` AS `destination_airport_code`,`i`.`marketing_airline_code` AS `marketing_airline_code`,`i`.`operating_airline_code` AS `operating_airline_code`,`i`.`flight_number` AS `flight_number`,`i`.`segment_status` AS `segment_status`,`i`.`cabin_class` AS `cabin_class`,`i`.`fare_id` AS `fare_id`,`f`.`flight_status` AS `flight_status`,`f`.`aircraft_type` AS `aircraft_type`,`f`.`distance_km` AS `distance_km`,`f`.`duration_min` AS `duration_min`,`f`.`no_of_stop` AS `no_of_stop`,`f`.`layover1_airport_code` AS `layover1_airport_code`,`f`.`layover1_min` AS `layover1_min`,`f`.`layover2_airport_code` AS `layover2_airport_code`,`f`.`layover2_min` AS `layover2_min`,`f`.`layover3_airport_code` AS `layover3_airport_code`,`f`.`layover3_min` AS `layover3_min`,`f`.`terminal_departure` AS `terminal_departure`,`f`.`terminal_arrival` AS `terminal_arrival`,`al`.`airline_code` AS `airline_code`,`al`.`airline_name` AS `airline_name`,`apd`.`airport_code` AS `dep_airport_code`,`apd`.`airport_name` AS `dep_airport_name`,`apd`.`city_name` AS `dep_city`,`apd`.`country_iso2` AS `dep_country_iso2`,`apd`.`timezone` AS `dep_timezone`,`apd`.`airport_city_display` AS `dep_airport_display`,`apa`.`airport_code` AS `arr_airport_code`,`apa`.`airport_name` AS `arr_airport_name`,`apa`.`city_name` AS `arr_city`,`apa`.`country_iso2` AS `arr_country_iso2`,`apa`.`timezone` AS `arr_timezone`,`apa`.`airport_city_display` AS `arr_airport_display`,`fr`.`travel_class` AS `fare_travel_class`,`fr`.`fare_family_code` AS `fare_family_code`,`fr`.`fare_family_name` AS `fare_family_name`,`fr`.`fare_basis` AS `fare_basis`,`fr`.`refundable` AS `refundable`,`fr`.`changeable` AS `changeable`,`fr`.`baggage_allowance` AS `baggage_allowance`,`fr`.`cabin_baggage` AS `cabin_baggage`,`fr`.`checkin_baggage` AS `checkin_baggage`,`fr`.`seat_included` AS `seat_included`,`fr`.`meal_included` AS `meal_included`,`fr`.`priority_included` AS `priority_included`,`fr`.`cancel_penalty` AS `cancel_penalty`,`fr`.`change_penalty` AS `change_penalty`,`fr`.`display_rank` AS `fare_display_rank`,`fr`.`base_fare` AS `fare_base_fare`,`fr`.`taxes` AS `fare_taxes`,`fr`.`fees` AS `fare_fees`,((`fr`.`base_fare` + `fr`.`taxes`) + `fr`.`fees`) AS `fare_total_calc`,`fr`.`currency` AS `fare_currency`,`bp`.`booking_passenger_id` AS `booking_passenger_id`,`bp`.`passenger_id` AS `passenger_id`,`bp`.`passenger_seq` AS `passenger_seq`,`bp`.`passenger_type` AS `passenger_type`,`bp`.`is_lead_passenger` AS `is_lead_passenger`,`bp`.`linked_adult_passenger_id` AS `linked_adult_passenger_id`,`bp`.`booking_passenger_status` AS `booking_passenger_status`,`bp`.`first_name_snapshot` AS `first_name_snapshot`,`bp`.`last_name_snapshot` AS `last_name_snapshot`,concat(`bp`.`first_name_snapshot`,' ',`bp`.`last_name_snapshot`) AS `passenger_name`,`bp`.`date_of_birth_snapshot` AS `date_of_birth_snapshot`,`bp`.`gender_snapshot` AS `gender_snapshot`,`bp`.`nationality_iso2_snapshot` AS `nationality_iso2_snapshot`,`bp`.`document_type_snapshot` AS `document_type_snapshot`,`bp`.`document_number_snapshot` AS `document_number_snapshot`,`bp`.`issuing_country_iso2_snapshot` AS `issuing_country_iso2_snapshot`,`bp`.`document_expiry_snapshot` AS `document_expiry_snapshot`,`bp`.`base_fare_amount` AS `pax_base_fare_amount`,`bp`.`tax_amount` AS `pax_tax_amount`,`bp`.`fee_amount` AS `pax_fee_amount`,`bp`.`line_total_amount` AS `pax_line_total_amount`,`bp`.`created_at` AS `booking_passenger_created_at`,`bp`.`updated_at` AS `booking_passenger_updated_at`,`p`.`passenger_uuid` AS `passenger_uuid`,`p`.`first_name` AS `passenger_first_name_master`,`p`.`last_name` AS `passenger_last_name_master`,`p`.`email` AS `passenger_email`,`p`.`phone` AS `passenger_phone`,`ip`.`itinerary_passenger_id` AS `itinerary_passenger_id`,`ip`.`seat_assignment` AS `seat_assignment`,`ip`.`ticket_number` AS `ticket_number`,`ip`.`coupon_number` AS `coupon_number`,`ip`.`segment_passenger_status` AS `segment_passenger_status`,`ip`.`checkin_status` AS `checkin_status`,`ip`.`boarding_status` AS `boarding_status`,`ip`.`baggage_status` AS `baggage_status`,`ip`.`meal_status` AS `meal_status`,`ip`.`meal_code` AS `meal_code`,`ip`.`ssr_code` AS `ssr_code`,`ip`.`remarks` AS `itinerary_passenger_remarks`,`ip`.`created_at` AS `itinerary_passenger_created_at`,`ip`.`updated_at` AS `itinerary_passenger_updated_at` from ((((((((((`itinerary` `i` join `booking` `b` on((`b`.`booking_reference` = `i`.`booking_reference`))) join `booking_passenger` `bp` on((`bp`.`booking_reference` = `b`.`booking_reference`))) join `itinerary_passenger` `ip` on(((`ip`.`segment_id` = `i`.`segment_id`) and (`ip`.`booking_passenger_id` = `bp`.`booking_passenger_id`)))) left join `passenger` `p` on((`p`.`passenger_id` = `bp`.`passenger_id`))) join `flight` `f` on((`f`.`flight_id` = `i`.`flight_id`))) join `airline` `al` on((`al`.`airline_code` = `f`.`airline_code`))) join `airport` `apd` on((`apd`.`airport_code` = `i`.`origin_airport_code`))) join `airport` `apa` on((`apa`.`airport_code` = `i`.`destination_airport_code`))) left join `fare` `fr` on((`fr`.`fare_id` = `i`.`fare_id`))) left join (select `p1`.`payment_id` AS `payment_id`,`p1`.`booking_reference` AS `booking_reference`,`p1`.`payment_method` AS `payment_method`,`p1`.`payment_status` AS `payment_status`,`p1`.`amount` AS `amount`,`p1`.`currency` AS `currency`,`p1`.`transaction_id` AS `transaction_id`,`p1`.`payment_date` AS `payment_date` from (`payment` `p1` join (select `payment`.`booking_reference` AS `booking_reference`,max(`payment`.`payment_id`) AS `max_payment_id` from `payment` group by `payment`.`booking_reference`) `p2` on(((`p2`.`booking_reference` = `p1`.`booking_reference`) and (`p2`.`max_payment_id` = `p1`.`payment_id`))))) `pay` on((`pay`.`booking_reference` = `b`.`booking_reference`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `vw_itinerary_details`
--

/*!50001 DROP VIEW IF EXISTS `vw_itinerary_details`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_itinerary_details` AS select `b`.`booking_reference` AS `booking_reference`,`b`.`passenger_id` AS `passenger_id`,`p`.`passenger_uuid` AS `passenger_uuid`,concat(`p`.`first_name`,' ',`p`.`last_name`) AS `passenger_name`,`p`.`email` AS `passenger_email`,`p`.`phone` AS `passenger_phone`,`b`.`booking_date` AS `booking_date`,`b`.`booking_status` AS `booking_status`,`b`.`payment_status` AS `payment_status`,`b`.`booking_source` AS `booking_source`,`b`.`currency` AS `booking_currency`,`b`.`total_amount` AS `booking_total_amount`,`i`.`segment_id` AS `segment_id`,`i`.`sequence_no` AS `sequence_no`,`i`.`cabin_class` AS `cabin_class`,`f`.`flight_id` AS `flight_id`,`f`.`flight_number` AS `flight_number`,`f`.`flight_status` AS `flight_status`,`f`.`aircraft_type` AS `aircraft_type`,`f`.`distance_km` AS `distance_km`,`f`.`duration_min` AS `duration_min`,`f`.`scheduled_departure` AS `scheduled_departure`,`f`.`scheduled_arrival` AS `scheduled_arrival`,`al`.`airline_code` AS `airline_code`,`al`.`airline_name` AS `airline_name`,`f`.`departure_airport` AS `dep_airport_code`,`apd`.`airport_name` AS `dep_airport_name`,`apd`.`city_name` AS `dep_city`,`apd`.`country_iso2` AS `dep_country_iso2`,`apd`.`timezone` AS `dep_timezone`,`f`.`arrival_airport` AS `arr_airport_code`,`apa`.`airport_name` AS `arr_airport_name`,`apa`.`city_name` AS `arr_city`,`apa`.`country_iso2` AS `arr_country_iso2`,`apa`.`timezone` AS `arr_timezone`,`i`.`fare_id` AS `fare_id`,`fr`.`travel_class` AS `fare_travel_class`,`fr`.`fare_family_code` AS `fare_family_code`,`fr`.`fare_family_name` AS `fare_family_name`,`fr`.`fare_basis` AS `fare_basis`,`fr`.`refundable` AS `refundable`,`fr`.`changeable` AS `changeable`,`fr`.`baggage_allowance` AS `baggage_allowance`,`fr`.`cabin_baggage` AS `cabin_baggage`,`fr`.`checkin_baggage` AS `checkin_baggage`,`fr`.`seat_included` AS `seat_included`,`fr`.`meal_included` AS `meal_included`,`fr`.`priority_included` AS `priority_included`,`fr`.`cancel_penalty` AS `cancel_penalty`,`fr`.`change_penalty` AS `change_penalty`,`fr`.`display_rank` AS `display_rank`,`fr`.`base_fare` AS `base_fare`,`fr`.`taxes` AS `taxes`,`fr`.`fees` AS `fees`,((`fr`.`base_fare` + `fr`.`taxes`) + `fr`.`fees`) AS `fare_total_calc`,`fr`.`currency` AS `fare_currency` from (((((((`itinerary` `i` join `booking` `b` on((`b`.`booking_reference` = `i`.`booking_reference`))) join `passenger` `p` on((`p`.`passenger_id` = `b`.`passenger_id`))) join `flight` `f` on((`f`.`flight_id` = `i`.`flight_id`))) join `airline` `al` on((`al`.`airline_code` = `f`.`airline_code`))) join `airport` `apd` on((`apd`.`airport_code` = `f`.`departure_airport`))) join `airport` `apa` on((`apa`.`airport_code` = `f`.`arrival_airport`))) left join `fare` `fr` on((`fr`.`fare_id` = `i`.`fare_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `vw_passenger_full`
--

/*!50001 DROP VIEW IF EXISTS `vw_passenger_full`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_0900_ai_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`shiva`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `vw_passenger_full` AS select `p`.`passenger_id` AS `passenger_id`,`p`.`passenger_uuid` AS `passenger_uuid`,`p`.`first_name` AS `first_name`,`p`.`last_name` AS `last_name`,`p`.`date_of_birth` AS `date_of_birth`,`p`.`gender` AS `gender`,`p`.`nationality_iso2` AS `nationality_iso2`,`p`.`email` AS `email`,`p`.`phone` AS `phone`,`p`.`created_at` AS `created_at`,`p`.`updated_at` AS `updated_at`,`pref`.`seat_preference` AS `seat_preference`,`pref`.`meal_preference` AS `meal_preference`,`pref`.`language_preference` AS `language_preference`,`passdoc`.`document_id` AS `passport_document_id`,`passdoc`.`document_number` AS `passport_number`,`passdoc`.`issuing_country_iso2` AS `passport_issuing_country`,`passdoc`.`expiry_date` AS `passport_expiry_date`,`passdoc`.`verification_status` AS `passport_verification_status`,`passdoc`.`scanned_copy_path` AS `passport_scanned_copy_path`,`visadoc`.`document_id` AS `visa_document_id`,`visadoc`.`document_number` AS `visa_number`,`visadoc`.`issuing_country_iso2` AS `visa_issuing_country`,`visadoc`.`expiry_date` AS `visa_expiry_date`,`visadoc`.`verification_status` AS `visa_verification_status`,`visadoc`.`scanned_copy_path` AS `visa_scanned_copy_path` from (((`passenger` `p` left join `passenger_preferences` `pref` on((`pref`.`passenger_id` = `p`.`passenger_id`))) left join `travel_documents` `passdoc` on((`passdoc`.`document_id` = (select `td`.`document_id` from `travel_documents` `td` where ((`td`.`passenger_id` = `p`.`passenger_id`) and (`td`.`document_type` = 'Passport')) order by (`td`.`expiry_date` is null),`td`.`expiry_date` desc,`td`.`created_at` desc limit 1)))) left join `travel_documents` `visadoc` on((`visadoc`.`document_id` = (select `td`.`document_id` from `travel_documents` `td` where ((`td`.`passenger_id` = `p`.`passenger_id`) and (`td`.`document_type` = 'Visa')) order by (`td`.`expiry_date` is null),`td`.`expiry_date` desc,`td`.`created_at` desc limit 1)))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Dumping events for database 'ars'
--

--
-- Dumping routines for database 'ars'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-26 19:27:22

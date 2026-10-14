DROP TABLE IF EXISTS hourly_demand;
DROP TABLE IF EXISTS weekday_demand;
DROP TABLE IF EXISTS daily_demand;
DROP TABLE IF EXISTS weekday_average;
DROP TABLE IF EXISTS period_demand;

CREATE TABLE hourly_demand AS
SELECT pickup_hour AS hour, COUNT(*) AS pickup_count
FROM trip GROUP BY pickup_hour;

CREATE TABLE weekday_demand AS 
SELECT CASE pickup_dow WHEN 0 THEN 'Monday' WHEN 1 THEN 'Tuesday' WHEN 2 THEN 'Wednesday' WHEN 3 THEN 'Thursday' WHEN 4 THEN 'Friday' WHEN 5 THEN 'Saturday' ELSE 'Sunday' END AS day_of_week, COUNT(*) AS pickup_count FROM trip GROUP BY pickup_dow;

CREATE TABLE daily_demand AS
SELECT date(pickup_datetime) AS date, COUNT(*) AS pickup_count
FROM trip GROUP BY date(pickup_datetime);

CREATE TABLE weekday_average AS 
SELECT w.day_of_week, w.pickup_count, d.day_count, ROUND(1.0 * w.pickup_count / d.day_count, 1) AS average_pickups
FROM weekday_demand w
JOIN (SELECT CASE strftime('%w', date) WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' ELSE 'Sunday' END AS day_of_week, COUNT(*) AS day_count FROM daily_demand GROUP BY 1) d ON d.day_of_week = w.day_of_week;

CREATE TABLE period_demand AS
SELECT CASE WHEN pickup_dow >= 5 THEN 'Weekend' ELSE 'Weekday' END AS period, COUNT(*) AS pickup_count FROM trip GROUP BY 1;



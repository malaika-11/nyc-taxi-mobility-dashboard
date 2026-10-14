# Person 1: Taxi Demand Analysis Algorithm

## 1. Purpose

The purpose of this algorithm is to identify when taxi demand is highest and lowest in New York City.It analyzes taxi pickup timestamps to calculate demand by hour, day of the week, weekday versus weekend, and calendar date.

## 2. Algorithm

1. Read the January 2019 yellow taxi trip dataset in chunks.
2. Select the pickup timestamp from each chunk.
3. Convert pickup timestamps into datetime values.
4. Exclude invalid timestamps and pickups outside January 2019.
5. Extracy the pickup hour, weekday, and calendar date.
6. Count pickups for each hour , weekday , date , and weekday/weekend period.
7. Write the aggregated results to CSV files.
8. Use the results to identify demand patterns.

## 3. Pseudocode

BEGIN 
     Initialize counters for hours, weekdays, dates, and periods

    FOR each chunk in the taxi dataset
         Read pickup timestamps
         Convert timestamps to datetime values
    
        FOR each valid timestamp
            IF timestamp is in January 2019
              Extract hour, weekday, and date
              Increment the corresponding counters
              Increment weekday or weekend counter
            END IF
        END FOR
    END FOR

    Write demand summaries to CSV files
END

## 4. Data Structures

- Dictionaries store pickup counts for each hour, weekday, date, and period.
- Chunked reading limits how much raw data must be processed in memory at once.
- CSV files store the aggregated results for further analysis and visualization

## 5. Time Complexity

Let n represent the number of trip records.

Each record is processed once. Therefore, the main counting operation takes O(n) time.

The script also writes a small number of summary rows. Sorting daily dates, if performed, takes O(d log d),where d is the number of distinct dates.

Overall, the time complexity id O(n + d log d).

## 6. Space Complexity

The script processes the raw dataset in chunks rather than loading the entire dataset into memory.

The counters store summaries rather than individual trips. If c is the chunk size and d is the number of distinct dates, the working space is approximately O(c + d)

## 7. Limitations

- The analysis focuses on pickup timestamps and does not explain why demand changes.
- The dataset represents January 2019, so the results may not represent other months or years.
- Pickup counts show demand volume but do not measure passenger waiting times or unmet demand.


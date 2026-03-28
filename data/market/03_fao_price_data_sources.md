# FAO Price Data Sources and Market Signal Types

## Source
FAO overview of price data and analysis sources.

## Metadata
- topic: market_price_data
- region: global
- source_type: official guide
- use_case: seasonal_price_trends_and_market_support
- market_scope: international_producer_wholesale_retail_consumer

## Overview
FAO provides multiple kinds of price information that can support agricultural market analysis. These data sources are useful for understanding price trends, comparing price levels across the supply chain, and distinguishing between international, producer, wholesale, retail, and consumer price indicators.

## Why This Matters for the System
The market component of the Smart Agriculture Advisor should not pretend to forecast exact real-time prices. Instead, it should use trusted public sources to explain:
- what type of price is being discussed
- whether a trend is international or domestic
- whether the value reflects farm-gate, wholesale, or retail conditions
- how seasonal price signals can support basic harvest-or-hold recommendations

## Main FAO Price Data Categories

### 1. International Prices
International prices include:
- export prices
- import prices

#### Export Prices
Export prices are prices in markets for products intended for delivery outside a country’s borders.
They are often valued as:
- free-on-rail
- free-alongside-ship
- free-on-board (f.o.b.)

#### Import Prices
Import prices are the prices of goods purchased inside a country but produced outside its borders.

### 2. FAO Food Price Index (FFPI)
The FAO Food Price Index is a measure of international prices for a basket of traded agricultural commodities.

#### Important Notes
- It is based on export prices
- It combines five commodity-group price indices
- The groups are weighted using average export shares from 2014–2016

### 3. Producer Prices
FAOSTAT Agricultural Producer Prices report official national-level data on prices received by farmers.

#### Important Notes
- These are farm-gate prices
- They refer to the point at which the produce leaves the farm
- They do not include:
  - transport beyond the farm gate
  - warehousing
  - processing
  - later selling costs

### 4. Producer Price Index
Producer Price Indices measure price inflation at the farm-gate level.

#### Use in the System
This is useful for:
- understanding whether producer prices are generally rising or falling
- explaining inflation pressure at the farm level
- giving context for producer profitability trends

### 5. Wholesale Prices
Wholesale prices are the prices at which wholesalers sell products in bulk quantities to:
- retailers
- manufacturers
- industrial users

#### Important Notes
Wholesale prices include:
- transportation charges after leaving the farm
- incidental expenses
- wholesaler profit margins

### 6. Retail Prices
Retail prices are the prices paid by end consumers.

#### Important Notes
Retail prices include:
- retailer expenses
- retailer profit margin
- all downstream costs reflected in final sale price

### 7. Consumer Price Indices (CPI and Food CPI)
FAOSTAT also provides:
- general Consumer Price Indices (CPI)
- Food Consumer Price Indices (Food-CPI)

#### Use in the System
These indices can help explain:
- food inflation
- changes in household food costs
- broader market pressure beyond the farm

### 8. FAO Data Lab High-Frequency Food Price Tool
FAO Data Lab monitors daily food prices and produces analytical tools and nowcasts.

#### Important Notes
- It uses daily prices on selected commodities
- It can support anomaly detection and short-term food price monitoring
- It is more useful for trend awareness than for exact local farm-level advice

## Price-Level Interpretation Rules

### Farm-Gate vs Wholesale vs Retail
The system should clearly distinguish:
- **farm-gate / producer price**: what the farmer receives
- **wholesale price**: bulk market price after intermediate handling and margins
- **retail price**: final consumer price

These are not interchangeable and should never be presented as if they mean the same thing.

### International vs Domestic
The system should also distinguish:
- **international prices**: export/import market context
- **domestic prices**: within-country producer, wholesale, or retail context

### Index vs Actual Price
A price index shows relative change over time, not the actual sale price of a specific product in a specific local market.

## Best Use in the Project
For the MVP, these FAO sources should be used to support:
- seasonal trend explanations
- price-type interpretation
- lightweight harvest-or-hold reasoning
- market-context responses
- curated historical trend summaries

## What Not to Claim
Do not claim:
- exact live local Lebanese market price predictions
- guaranteed selling recommendations
- precise same-day farm-gate prices unless directly provided from a trusted dataset

## Safe Recommendation Style
The system can say things like:
- producer prices and retail prices are different and should not be compared directly
- current signals suggest upward or downward seasonal pressure
- storage may make sense only if quality can be preserved and price seasonality supports waiting
- international commodity trends do not always match local farm-gate conditions

## Notes for System Use
Use this document for:
- explaining different price data types
- grounding market-agent answers
- supporting seasonal trend interpretation
- avoiding confusion between producer, wholesale, retail, and CPI data
- justifying curated market datasets for the MVP
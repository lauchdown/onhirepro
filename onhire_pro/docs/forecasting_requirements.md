# Forecasting Requirements for OnHire Pro

## Overview
This document outlines the requirements for implementing forecasting capabilities within the OnHire Pro application. The forecasting module will provide predictive insights for key performance indicators (KPIs), enabling better business planning and decision-making.

## KPIs Suitable for Forecasting

The following KPIs have been identified as suitable candidates for forecasting based on their business relevance and data characteristics:

1. **Item Utilization Rate**
   - Business value: Critical for inventory planning and procurement decisions
   - Data characteristics: Time-series data with potential seasonality
   - Forecasting horizon: 30, 60, and 90 days

2. **Rental Revenue**
   - Business value: Essential for financial planning and budgeting
   - Data characteristics: Time-series data with potential seasonality and trends
   - Forecasting horizon: 30, 60, and 90 days

3. **Booking Conversion Rate**
   - Business value: Important for sales strategy and marketing planning
   - Data characteristics: Time-series data with potential correlation to marketing activities
   - Forecasting horizon: 30 and 60 days

4. **Average Rental Duration**
   - Business value: Useful for inventory planning and pricing strategy
   - Data characteristics: Time-series data with potential seasonality
   - Forecasting horizon: 30 and 60 days

5. **Maintenance Turnaround Time**
   - Business value: Critical for operational planning and resource allocation
   - Data characteristics: Time-series data with potential correlation to workload
   - Forecasting horizon: 30 days

## Forecasting Algorithm Requirements

### Data Collection
- Historical data must be collected for each KPI at daily intervals
- Minimum historical data required: 90 days (ideally 365 days for seasonal patterns)
- Data should be stored in a structured format with timestamps
- Missing data points should be handled through interpolation

### Algorithm Selection
- Time-series forecasting algorithms are required
- Primary algorithm: Prophet (Facebook/Meta's forecasting library)
  - Handles seasonality, holidays, and missing data well
  - Provides uncertainty intervals
  - Works with limited historical data
- Secondary algorithms for comparison:
  - ARIMA (Auto-Regressive Integrated Moving Average)
  - Exponential Smoothing

### Model Features
- Seasonality detection (weekly, monthly, quarterly)
- Trend detection and modeling
- Outlier detection and handling
- Confidence intervals for forecasts
- Ability to incorporate external factors (e.g., holidays, marketing campaigns)

### Performance Metrics
- Mean Absolute Percentage Error (MAPE)
- Root Mean Square Error (RMSE)
- Forecast accuracy should be evaluated using cross-validation

## Data Storage Requirements

### Forecasted KPI Value DocType
A new DocType is required to store forecasted values with the following fields:

- `name`: Auto-generated primary key
- `kpi_name`: Link to KPI definition
- `forecast_date`: Date of the forecast generation
- `target_date`: Date for which the value is forecasted
- `forecasted_value`: Float field for the forecasted value
- `lower_bound`: Float field for the lower confidence interval
- `upper_bound`: Float field for the upper confidence interval
- `algorithm`: Select field for the algorithm used
- `accuracy`: Float field for the forecast accuracy
- `historical_data_points`: Integer field for the number of data points used
- `company`: Link to Company

### Historical KPI Value DocType
A DocType to store historical KPI values for training the forecasting models:

- `name`: Auto-generated primary key
- `kpi_name`: Link to KPI definition
- `date`: Date of the KPI value
- `actual_value`: Float field for the actual KPI value
- `company`: Link to Company
- `filters_json`: JSON field to store the filters used to calculate the value

## Implementation Requirements

### Libraries and Dependencies
- Python libraries:
  - prophet (Facebook/Meta's forecasting library)
  - pandas (for data manipulation)
  - numpy (for numerical operations)
  - scikit-learn (for evaluation metrics)
  - matplotlib (for visualization)

### Scheduled Tasks
- Daily collection of KPI values (end of day)
- Weekly generation of forecasts (weekend)
- Monthly evaluation of forecast accuracy

### Integration Points
- Dashboard integration to display forecasted values alongside actual values
- Alerts for significant deviations from forecasts
- Export functionality for forecast data

## User Interface Requirements

### Forecast Visualization
- Line charts showing historical data and forecasted values
- Shaded areas for confidence intervals
- Ability to toggle between different forecasting horizons
- Comparison view of different forecasting algorithms

### Configuration Interface
- Settings to configure forecasting parameters
- Ability to include/exclude specific KPIs from forecasting
- Configuration of alert thresholds for forecast deviations

## Security and Access Control

### Role-Based Access
- Forecast viewing: All users with dashboard access
- Forecast configuration: System Manager, Analytics Manager
- Algorithm selection and tuning: System Manager

### Data Isolation
- Forecasts must respect company-level data isolation
- Users should only see forecasts for companies they have access to

## Performance Considerations

### Computational Requirements
- Forecasting calculations should be performed asynchronously
- Resource-intensive operations should be scheduled during off-peak hours
- Caching of forecast results to minimize recalculation

### Scalability
- Solution should handle forecasting for up to 50 KPIs
- Performance should remain acceptable with 3+ years of historical data
- Ability to distribute computation across multiple workers if needed

## Implementation Phases

### Phase 1: Core Infrastructure
- Create DocTypes for storing historical and forecasted values
- Implement data collection mechanisms
- Set up scheduled tasks

### Phase 2: Basic Forecasting
- Implement Prophet-based forecasting for top 3 KPIs
- Create basic visualization
- Implement accuracy evaluation

### Phase 3: Advanced Features
- Add additional algorithms
- Implement confidence intervals
- Create advanced visualization
- Add alerting mechanisms

### Phase 4: Optimization
- Tune algorithms for better accuracy
- Optimize performance
- Implement caching strategies

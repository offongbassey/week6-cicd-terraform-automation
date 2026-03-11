# ==========================================
# SNS Topic for Alarm Notifications
# ==========================================
# This creates a "mailing list" for CloudWatch alarms
# When an alarm triggers, it sends a message to this topic
# Everyone subscribed to this topic gets the notification

resource "aws_sns_topic" "lambda_alerts" {
  # Name of the topic (like naming a mailing list)
  name = "lambda-monitoring-alerts"
  
  # Human-readable description
  display_name = "Lambda Monitoring Alerts"
  
  # Tags help organize resources in AWS
  tags = {
    Name        = "Lambda Alerts"
    Project     = var.project_name
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

# Email Subscription to SNS Topic
# ==========================================
# This subscribes your email to the topic
# When the topic receives a message, you get an email
# NOTE: You'll need to confirm the subscription via email!

resource "aws_sns_topic_subscription" "lambda_alerts_email" {
  # Which topic should this subscription be for?
  # We're referencing the topic we just created above
  topic_arn = aws_sns_topic.lambda_alerts.arn
  
  # How should notifications be delivered?
  # Options: email, sms, https, lambda, sqs
  protocol = "email"
  
  # Where should notifications be sent?
  # This is your email address
  endpoint = "kinqzbitz@gmail.com"
}

# ==========================================
# Alarm 1: Lambda High Error Rate
# ==========================================
# This alarm watches for Lambda function errors
# If Lambda has more than 1 error in 5 minutes → triggers alarm
# Alarm sends notification to SNS topic → you get email

resource "aws_cloudwatch_metric_alarm" "lambda_high_error_rate" {
  # Name of the alarm (what you see in AWS Console)
  alarm_name = "Lambda-High-Error-Rate"
  
  # Optional: comparison operator for the alarm
  # English: "Trigger if metric is GREATER THAN threshold"
  comparison_operator = "GreaterThanThreshold"
  
  # How many periods must breach threshold before alarming?
  # 1 = Alarm immediately on first breach
  # 2 = Must breach twice in a row before alarming
  evaluation_periods = 1
  
  # Which metric should we watch?
  # This is a built-in AWS metric for Lambda errors
  metric_name = "Errors"
  
  # Which AWS service does this metric come from?
  namespace = "AWS/Lambda"
  
  # How long is each evaluation period?
  # 300 seconds = 5 minutes
  # Alarm checks: "How many errors in the last 5 minutes?"
  period = 300
  
  # What math should we do on the metric?
  # Sum = Add up all errors in the period
  # Average = Average number of errors
  # Maximum = Highest error count
  # We use Sum: "Total errors in 5 minutes"
  statistic = "Sum"
  
  # What's the threshold (limit)?
  # If errors > 1 → trigger alarm
  threshold = 1
  
  # What actions should happen when alarm triggers?
  # This sends a message to our SNS topic
  alarm_actions = [aws_sns_topic.lambda_alerts.arn]
  
  # Human-readable description
  alarm_description = "This alarm triggers when Lambda has errors"
  
  # Which specific Lambda function should we monitor?
  # Dimensions = Filters (like WHERE clause in SQL)
  dimensions = {
    FunctionName = aws_lambda_function.file_processor.function_name
  }
  
  # How should we treat missing data?
  # notBreaching = If no data, assume everything is OK
  # Options: missing, ignore, breaching, notBreaching
  treat_missing_data = "notBreaching"
  
  # Tags for organization
  tags = {
    Name    = "Lambda High Error Rate Alarm"
    Project = var.project_name
  }
}

# ==========================================
# Alarm 2: Lambda High Invocations
# ==========================================
# This alarm watches for unusually high Lambda invocations
# Could indicate: attack, infinite loop, or runaway process
# If Lambda runs more than 50 times in 5 minutes → alarm

resource "aws_cloudwatch_metric_alarm" "lambda_high_invocations" {
  alarm_name          = "Lambda-High-Invocations"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Invocations"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 50
  alarm_actions       = [aws_sns_topic.lambda_alerts.arn]
  alarm_description   = "Triggers when Lambda invocations are unusually high"
  
  dimensions = {
    FunctionName = aws_lambda_function.file_processor.function_name
  }
  
  treat_missing_data = "notBreaching"
  
  tags = {
    Name    = "Lambda High Invocations Alarm"
    Project = var.project_name
  }
}

# ==========================================
# Alarm 3: Lambda Processing Failures
# ==========================================
# This alarm watches YOUR CUSTOM METRIC!
# Uses the ProcessingErrors metric you publish from Lambda code
# If ANY processing error occurs → alarm immediately

resource "aws_cloudwatch_metric_alarm" "lambda_processing_failures" {
  alarm_name          = "Lambda-Processing-Failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  
  # This is YOUR custom metric!
  metric_name = "ProcessingErrors"
  
  # This is YOUR custom namespace!
  namespace = "LambdaFileProcessor"
  
  # Check every 1 minute (faster than the others!)
  period = 60
  
  statistic     = "Sum"
  threshold     = 0  # ANY error triggers alarm!
  alarm_actions = [aws_sns_topic.lambda_alerts.arn]
  
  alarm_description = "Triggers on any Lambda processing errors"
  
  # No dimensions needed - your custom metric is already specific
  
  treat_missing_data = "notBreaching"
  
  tags = {
    Name    = "Lambda Processing Failures Alarm"
    Project = var.project_name
  }
}
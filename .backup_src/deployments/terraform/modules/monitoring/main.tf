# ==============================================================================
# Monitoring Module — CloudWatch Dashboard & SRE Operations Alarms
# ==============================================================================

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "eks_cluster_id" {
  type = string
}

variable "rds_id" {
  type = string
}

variable "redis_id" {
  type = string
}

variable "msk_cluster_arn" {
  type = string
}

# ── CloudWatch Dashboard ───────────────────────────────────────────────────────

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", var.rds_id]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "PostgreSQL RDS CPU Utilization"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", var.redis_id]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "Redis ElastiCache CPU Utilization"
        }
      }
    ]
  })
}

# ── CloudWatch Alarm: RDS CPU Usage high ───────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "rds_high_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-high-cpu"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "This alarm triggers if RDS PostgreSQL CPU exceeds 85% for 10 minutes"
  actions_enabled     = false

  dimensions = {
    DBInstanceIdentifier = var.rds_id
  }
}

# ── CloudWatch Alarm: RDS Storage space low ────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "rds_low_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-low-storage"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 10000000000 # 10 GB in bytes
  alarm_description   = "This alarm triggers if PostgreSQL RDS free storage space drops below 10GB"
  actions_enabled     = false

  dimensions = {
    DBInstanceIdentifier = var.rds_id
  }
}

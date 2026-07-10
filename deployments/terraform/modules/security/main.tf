# ==============================================================================
# Security Module — Production KMS Keys, Secrets Manager, and AWS WAF Web ACL
# ==============================================================================

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

# ── KMS Keys ──────────────────────────────────────────────────────────────────

resource "aws_kms_key" "main" {
  description             = "KMS Master Key for CloudScale ${var.environment} encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-${var.environment}-kms"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.project_name}-${var.environment}-key"
  target_key_id = aws_kms_key.main.key_id
}

# ── Secrets Manager ────────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.project_name}/${var.environment}/database"
  kms_key_id              = aws_kms_key.main.key_id
  recovery_window_in_days = 0

  tags = {
    Name = "${var.project_name}-${var.environment}-db-secret"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials_placeholder" {
  secret_id     = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = "cloudscale_admin"
    password = "SuperSecurePassword123!" # Will be updated/rotated dynamically
  })
}

resource "aws_secretsmanager_secret" "jwt_signing_key" {
  name                    = "${var.project_name}/${var.environment}/jwt"
  kms_key_id              = aws_kms_key.main.key_id
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "jwt_placeholder" {
  secret_id     = aws_secretsmanager_secret.jwt_signing_key.id
  secret_string = jsonencode({
    secret_key = "SuperSecretSigningKeyForJWTValidation2026!"
  })
}

# ── AWS WAF (Web Application Firewall) ─────────────────────────────────────────

resource "aws_wafv2_web_acl" "main" {
  name        = "${var.project_name}-${var.environment}-waf"
  description = "AWS WAF Web ACL protecting CloudScale public interfaces"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Rule 1: IP Rate Limiting (Block requests exceeding 1000 per 5 minutes)
  rule {
    name     = "IPRateLimit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 1000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "WAF_IPRateLimit"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: AWS Managed Common Rule Set (OWASP Top 10, Local File Inclusion, etc)
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "WAF_CommonRules"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed SQLi Rule Set
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "WAF_SQLiRules"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "WAF_Main_WebACL"
    sampled_requests_enabled   = true
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-waf-acl"
  }
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "kms_key_arn" {
  value = aws_kms_key.main.arn
}

output "db_secret_arn" {
  value = aws_secretsmanager_secret.db_credentials.arn
}

output "jwt_secret_arn" {
  value = aws_secretsmanager_secret.jwt_signing_key.arn
}

output "waf_web_acl_arn" {
  value = aws_wafv2_web_acl.main.arn
}

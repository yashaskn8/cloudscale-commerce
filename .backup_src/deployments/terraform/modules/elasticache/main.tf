# ==============================================================================
# ElastiCache Module — Production Redis Cluster with Replication & Encryption
# Features replication groups, transit/at-rest encryption, auto-failover.
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

variable "private_subnet_ids" {
  type = list(string)
}

variable "node_type" {
  type = string
}

variable "num_cache_clusters" {
  type = number
}

variable "kms_key_arn" {
  type = string
}

variable "eks_security_group_id" {
  type = string
}

# ── Redis Subnet Group ─────────────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids
}

# ── Security Group ─────────────────────────────────────────────────────────────

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-${var.environment}-redis-sg"
  description = "Security group for Redis ElastiCache replication group"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from EKS Nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.eks_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-redis-sg"
  }
}

# ── Parameter Group ────────────────────────────────────────────────────────────

resource "aws_elasticache_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

# ── Redis Replication Group (Active Cluster Core) ──────────────────────────────

resource "aws_elasticache_replication_group" "main" {
  replication_group_id        = "${var.project_name}-${var.environment}-redis"
  description                 = "Production cache clustering for CloudScale"
  node_type                   = var.node_type
  num_cache_clusters          = var.num_cache_clusters
  port                        = 6379
  parameter_group_name        = aws_elasticache_parameter_group.main.name
  subnet_group_name           = aws_elasticache_subnet_group.main.name
  security_group_ids          = [aws_security_group.redis.id]

  automatic_failover_enabled  = true
  multi_az_enabled            = true

  at_rest_encryption_enabled  = true
  transit_encryption_enabled  = true
  kms_key_id                  = var.kms_key_arn

  snapshot_retention_limit    = 7
  snapshot_window             = "02:00-03:00"
  maintenance_window          = "mon:03:30-mon:04:30"

  tags = {
    Name = "${var.project_name}-${var.environment}-redis"
  }
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "replication_group_id" {
  value = aws_elasticache_replication_group.main.id
}

output "primary_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "reader_endpoint" {
  value = aws_elasticache_replication_group.main.reader_endpoint_address
}

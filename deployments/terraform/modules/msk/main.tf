# ==============================================================================
# MSK Module — Production Amazon Managed Streaming for Apache Kafka
# Features multi-broker topology, disk/transit encryption, and CloudWatch metrics.
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

variable "broker_instance_type" {
  type = string
}

variable "broker_count" {
  type = number
}

variable "ebs_volume_size" {
  type = number
}

variable "kms_key_arn" {
  type = string
}

variable "eks_security_group_id" {
  type = string
}

# ── Security Group ─────────────────────────────────────────────────────────────

resource "aws_security_group" "msk" {
  name        = "${var.project_name}-${var.environment}-msk-sg"
  description = "Security group for MSK Kafka cluster"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Kafka TLS from EKS Nodes"
    from_port       = 9094
    to_port         = 9094
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
    Name = "${var.project_name}-${var.environment}-msk-sg"
  }
}

# ── CloudWatch Logging ─────────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.project_name}-${var.environment}"
  retention_in_days = 30
}

# ── MSK Kafka Cluster ──────────────────────────────────────────────────────────

resource "aws_msk_cluster" "main" {
  cluster_name           = "${var.project_name}-${var.environment}-kafka"
  kafka_version          = "3.4.0"
  number_of_broker_nodes = var.broker_count

  broker_node_group_info {
    instance_type   = var.broker_instance_type
    client_subnets  = var.private_subnet_ids
    security_groups = [aws_security_group.msk.id]
    storage_info {
      ebs_storage_info {
        volume_size = var.ebs_volume_size
      }
    }
  }

  encryption_info {
    encryption_at_rest {
      data_volume_kms_key_arn = var.kms_key_arn
    }
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  open_monitoring {
    prometheus {
      jmx_exporter {
        enabled_in_broker = true
      }
      node_exporter {
        enabled_in_broker = true
      }
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-msk"
  }
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "cluster_arn" {
  value = aws_msk_cluster.main.arn
}

output "bootstrap_brokers_tls" {
  value = aws_msk_cluster.main.bootstrap_brokers_tls
}

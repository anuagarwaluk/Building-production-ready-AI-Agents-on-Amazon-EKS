################################################################################
# ECR repositories, one per component
################################################################################

resource "aws_ecr_repository" "customer_agent" {
  name                 = "agents-on-eks/customer-agent"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

resource "aws_ecr_repository" "shop_mcp" {
  name                 = "agents-on-eks/shop-mcp"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

resource "aws_ecr_repository" "chat_ui" {
  name                 = "agents-on-eks/chat-ui"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

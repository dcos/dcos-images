variable "aws_default_os_user" {
 type = "map"
   default = {
    oracle  = "oracle"
   }
}

variable "aws_ami" {
 type = "map"
   default = {
    oracle_us-west-2 = "ami-dcc58ea4"
  }
}

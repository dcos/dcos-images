for region in `aws ec2 describe-regions --output text | cut -f3`
do
  echo "region: $region:"
  aws ec2 describe-images \
    --owners 'aws-marketplace' \
    --region "$region" \
    --filters 'Name=product-code,Values=aw0evgkw8e5c1q413zgy5pjce' \
    --query 'Images[*].{ID:ImageId}' \
    --output 'json'
done

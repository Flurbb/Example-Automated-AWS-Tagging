# Example Automated Tagging Remediation

This repo contains the Cloudformation templates and Python code to deploy an automated tagging remediation system to a single account.

In an enterprise environment dealing with multiple accounts the DynamoDB table would be deployed to a centralized account with an associated role that can be assumed from the Lambdas in your other accounts.

The Lambdas would need to be updated to use an sts client to assume into the central account and have the dynamodb client created using that role.

Things like bucket names and table names have been hardcoded because I procrastinated setting up these templates until the night before I was giving a presentation on this architecture.

In order for the lambdas to work correctly you'll need to add at least 1 item to the DynamoDB table named `Default` which contains a list called `Tags` containing all the tags you'd like to require.

Additional, resource type specific required tags items can be added using the [AWS Resource Type Reference Format](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) as the `resource_type` of the table item.

#### This project was originally built in Terraform which has a few advantages from a maintenance perspective:
    
1 All of the resources that have to be created per-resource type you're evaluating can be created utilizing `for_each` to iterate over a map of all the resource types you'd like to cover.

2 Terraform supports DynamoDB Table Items so you can store the items with your required tags for each resource type as versioned Terraform code instead of adding them after the fact.

#### To expand this project to cover additional resource types using the Cloudformation templates provided you'll need to add the relevant items listed in each of the TODO comments

The Google Slides presentation created to go along with this code can be found [here](https://docs.google.com/presentation/d/11OIZ6X33kyDw1GjmgrgpIyMOSB6OAMgJW_7ijRU4KjY/edit?usp=sharing)

I'll edit this README to include a link to the YouTube video of the presentation once it is posted.
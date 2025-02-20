import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.linkedin import LinkedInCompany, Funding, FundingType
from services.firestore import db


def convert_to_linkedin_company(company_data: dict) -> LinkedInCompany:
    """Convert raw company data to LinkedInCompany object."""

    funding = []

    for funding_event in company_data.get("funding_data", {}):
        funding.append(
            Funding(
                funding_type=funding_event.get(
                    "fundraising_event", FundingType.UNKNOWN
                ),
                money_raised=funding_event.get("amount_raised", None)
                if funding_event.get("amount_raised") != ""
                else None,
                announced_date=funding_event.get("date"),
                investor_list=funding_event.get("investors", []),
                number_of_investors=len(funding_event.get("investors", [])),
            )
        )

    # Create LinkedInCompany object with the new structure
    company = LinkedInCompany(
        company_id=company_data.get("company_id", ""),
        name=company_data.get("name", ""),
        website=company_data.get("website"),
        linkedin=company_data.get("linkedin"),
        crunchbase=company_data.get("crunchbase"),
        location=company_data.get("location"),
        description=company_data.get("description"),
        industries=company_data.get("industries", []),
        funding_data=funding,
        founded_on=company_data.get("founded_on"),
        ipo_status=company_data.get("ipo_status"),
        operating_status=company_data.get("operating_status"),
    )

    return company


def main():
    # Read the process.json file
    with open(os.path.join(os.path.dirname(__file__), "good.json"), "r") as f:
        companies_data = json.load(f)

    # Process each company
    if isinstance(companies_data, dict):
        companies_data = [companies_data][:2]  # Convert single company to list

    # Create a batch
    batch = db.batch()
    count = 0
    batch_size = 500  # Firestore's maximum batch size is 500

    for company_data in companies_data:
        try:
            # Convert to LinkedInCompany object
            company = convert_to_linkedin_company(company_data)

            # Get company ID
            company_id = company.company_id
            if not company_id:
                print(f"Skipping company {company.name} - no ID found")
                continue

            # Add to batch instead of individual write
            company_dict = company.dict()
            batch.set(db.collection("companies").document(company_id), company_dict)
            count += 1

            # If we've reached batch size limit, commit and create new batch
            if count >= batch_size:
                batch.commit()
                print(f"Successfully uploaded batch of {count} companies")
                batch = db.batch()
                count = 0

        except Exception as e:
            print(f"Error processing company: {str(e)}")

    # Commit any remaining companies in the final batch
    if count > 0:
        batch.commit()
        print(f"Successfully uploaded final batch of {count} companies")


if __name__ == "__main__":
    main()

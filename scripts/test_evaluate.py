import requests
import json

def test_evaluate_no_paraform():
    # API endpoint
    url = "http://localhost:8000/evaluate-no-paraform"

    # Test payload
    payload = {
        "job_description": """
        Manager, Talent Acquisition
Molina Healthcare • Long Beach, CA • via ZipRecruiter
4 days ago
Full-time
Health insurance
Apply on ZipRecruiter
Apply on Glassdoor
Apply on SimplyHired
Apply on Talentify
Apply on WhatJobs
Apply on JobsMarket.io
Apply on JobsNearMe.AI
Apply on Jobrapido.com
Job highlights
Identified by Google from the original job post
Qualifications
Experience building and leading high performing recruiting teams
Demonstrated experience recruiting for both technical and non-technical roles
Display a proven ability to understand strategic organizational issues and offer effective solutions
Ability to simultaneously manage multiple searches, candidates at different stages, and various recruitment projects
Experience leveraging data and analysis to identify problems and drive meaningful results
Excellent negotiation and critical thinking skills, with the ability to skillfully set and manage expectations throughout the recruitment process
Strikingly unique balance of excellent communication and time management skills coupled with an extreme attention to detail and sense of urgency
Understanding of the importance in creating and influencing company culture in your role
Warm, positive, personable with a genuine interest in people
You set the tone and tend to attract people to you
Experience working with an Applicant Tracking System
Required Education
BS/BA degree
Required Experience
5+ years of full cycle recruiting
2+ years leading a recruiting team
Responsibilities
As a Manager of Talent Acquisition, You will partner with the Manager, Talent Acquisition Operations & Onboarding and AVP, Talent Acquisition and you'll be responsible for overseeing the operations, staff and services of a team of corporate recruiters
You will provide leadership to ensure sourcing and recruiting activities, attract, recruit, retain and develop top talent
This responsibility includes managing the performance of a recruitment team overseeing company-wide positions
Partner with HR and business leaders to build well-defined recruitment strategies that support the needs of the long term organizational objectives
Develop, implement and execute tactical sourcing strategies aimed at generating candidate flow and creating a rich talent pool to support all current and future hiring needs
Identify strategies for engaging and closing the best candidates for critical pipeline positions
Own all aspects of the full-cycle recruitment processes including sourcing, outreach communication, interview plan development, scheduling, offer creation and negotiation
Recommend compensation, benefits and retention strategies to the leadership team
Ensure a positive candidate experience throughout all touch points of the recruitment process
Leverage our applicant tracking system to define, develop and analyze recruitment analytics to guide process refinement
Identify and execute innovative employer branding initiatives
Job description
Job Description

Job Summary
As a Manager of Talent Acquisition, You will partner with the Manager, Talent Acquisition Operations & Onboarding and AVP, Talent Acquisition and you'll be responsible for overseeing the operations, staff and services of a team of corporate recruiters. You will provide leadership to ensure sourcing and recruiting activities, attract, recruit, retain and develop top talent. This responsibility includes managing the performance of a recruitment team overseeing company-wide positions.

Knowledge/Skills/Abilities

Partner with HR and business leaders to build well-defined recruitment strategies that support the needs of the long term organizational objectives
Develop, implement and execute tactical sourcing strategies aimed at generating candidate flow and creating a rich talent pool to support all current and future hiring needs
Identify strategies for engaging and closing the best candidates for critical pipeline positions
Own all aspects of the full-cycle recruitment processes including sourcing, outreach communication, interview plan development, scheduling, offer creation and negotiation
Recommend compensation, benefits and retention strategies to the leadership team
Ensure a positive candidate experience throughout all touch points of the recruitment process
Leverage our applicant tracking system to define, develop and analyze recruitment analytics to guide process refinement
Serve as a company ambassador to promote Molina Healthcare as a top employment destination by clearly articulating our value proposition in a highly competitive market
Identify and execute innovative employer branding initiatives
Experience building and leading high performing recruiting teams
Demonstrated experience recruiting for both technical and non-technical roles
Display a proven ability to understand strategic organizational issues and offer effective solutions
Ability to simultaneously manage multiple searches, candidates at different stages, and various recruitment projects
Experience leveraging data and analysis to identify problems and drive meaningful results
Excellent negotiation and critical thinking skills, with the ability to skillfully set and manage expectations throughout the recruitment process
Strikingly unique balance of excellent communication and time management skills coupled with an extreme attention to detail and sense of urgency
Understanding of the importance in creating and influencing company culture in your role
Warm, positive, personable with a genuine interest in people. You set the tone and tend to attract people to you
Experience working with an Applicant Tracking System.

Job Qualifications

Required Education

BS/BA degree

Required Experience

5+ years of full cycle recruiting

2+ years leading a recruiting team

To all current Molina employees: If you are interested in applying for this position, please apply through the intranet job listing.

Molina Healthcare offers a competitive benefits and compensation package. Molina Healthcare is an Equal Opportunity Employer (EOE) M/F/D/V.
        """,
        "url": "https://www.linkedin.com/in/ellina-oganyan-68857113a/"
    }

    # Make the POST request
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Print the response in a formatted way
        print("Status Code:", response.status_code)
        print("\nResponse:")
        print(json.dumps(response.json(), indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    test_evaluate_no_paraform()
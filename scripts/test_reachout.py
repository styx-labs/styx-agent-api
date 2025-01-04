import requests
import json

def test_reachout():
    # API endpoint
    url = "http://localhost:8000/generate-reachout-headless"

    # Test payload
    payload = {
        "name": "Ellina Oganyan",
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
        """,
        "sections": [
            {
                "section": "Recommendation",
                "content": "Ellina Oganyan is a strong fit for the Manager, Talent Acquisition position at Molina Healthcare. With over five years of full-cycle recruiting experience and demonstrated leadership in managing recruitment teams, she possesses the necessary skills to oversee and enhance recruitment processes effectively. Her strategic problem-solving abilities, combined with strong communication and negotiation skills, position her well to contribute to the organization's talent acquisition goals.",
            },
            {
                "section": "Leadership and team management",
                "content": "Ellina Oganyan has demonstrated significant leadership and team management skills in her role as Recruiting Manager at Lunar Energy, where she oversees a team of five in the HR department. Her previous positions, including Talent Acquisition Manager and Executive Manager, further indicate her capability in managing recruitment processes and strategies effectively. This diverse experience in various roles within recruitment showcases her ability to lead teams and contribute to organizational growth, making her a valuable asset in leadership roles within the recruitment sector.",
            },
            {
                "section": "Full-cycle recruiting expertise",
                "content": "Ellina Oganyan demonstrates strong full-cycle recruiting expertise as the Recruiting Manager at Lunar Energy, where she oversees recruitment processes and strategies. Her diverse background includes roles such as Talent Acquisition Manager and Executive Manager at various companies, indicating a comprehensive understanding of the recruitment lifecycle. Her leadership in the HR department at Lunar Energy further emphasizes her capabilities in talent acquisition and management, making her a significant asset in her current role.",
            },
            {
                "section": "Data-driven decision making",
                "content": "Ellina Oganyan's role as Recruiting Manager at Lunar Energy indicates her involvement in data-driven decision making, particularly in recruitment strategies. However, specific examples of her use of data analytics or metrics in her decision-making processes are not provided in the sources. Her diverse background in recruitment suggests a familiarity with data-driven approaches, but without explicit evidence, it is difficult to assess her proficiency in this area. Overall, she demonstrates potential in data-driven decision making, warranting a moderate score.",
            },
            {
                "section": "Excellent communication and negotiation skills",
                "content": "Ellina Oganyan has demonstrated strong communication and negotiation skills through her extensive experience in recruitment and talent acquisition. As the Recruiting Manager at Lunar Energy, she oversees recruitment processes and strategies, indicating her ability to effectively communicate with candidates and stakeholders. Her diverse background in various recruitment roles, including Talent Acquisition Manager and Executive Manager, further supports her proficiency in negotiation and communication within the industry. However, specific examples of her negotiation successes were not found in the provided sources.",
            }
        ],
        "citations": [
    {
      "index": 1,
      "url": "https://theorg.com/org/lunar-energy/org-chart/ellina-oganyan",
      "confidence": 1.0,
      "distilled_content": "Ellina Oganyan is the Recruiting Manager at Lunar Energy, showcasing her expertise in recruitment and talent acquisition. With a diverse professional background, she has worked in various roles including Talent Acquisition Manager and Executive Manager at companies like The Recruitment Depot, Caroo, and Jobot. Ellina holds a Bachelor's degree in Marketing from California State University, Fullerton, which complements her unique blend of human and robotic qualities in her career. This information highlights her qualifications and experience in the field of recruitment, making her a significant figure in her current role at Lunar Energy."
    },
    {
      "index": 2,
      "url": "https://rocketreach.co/lunar-energy-management_b7f61f5bc2af8565",
      "confidence": 1.0,
      "distilled_content": "The source is an organizational chart from Lunar Energy, detailing the management team and structure of the company. Ellina Oganyan is identified as the Recruiting Manager at Lunar Energy, which employs a total of 261 staff members. This information is relevant as it highlights her role within the company, indicating her responsibilities in recruitment and talent acquisition, which are crucial for the company's growth and operational success. The context of her position within the management team alongside other key figures, such as Kunal Girotra (Founder and CEO) and Anu Bhagwat (Head of Technical Programs), underscores her importance in the organizational hierarchy."
    },
    {
      "index": 3,
      "url": "https://rocketreach.co/ellina-oganyan-email_82511471",
      "confidence": 0.9,
      "distilled_content": "Ellina Oganyan is a Recruiting Manager at Lunar Energy, based in Irvine, CA. She has a diverse background in recruitment, having held various positions including Executive Manager and Principal Recruiter at Jobot, and Talent Acquisition Manager at Caroo. Ellina's educational background includes a degree from California State University-Fullerton. Her current role at Lunar Energy, which she has held since 2022, highlights her expertise in the energy sector, making her a key player in the recruitment of talent for this industry. The source provides contact information, including two email addresses and a phone number, indicating her accessibility for professional inquiries."
    },
    {
      "index": 4,
      "url": "https://www.linkedin.com/posts/scott-filbin_recruiting-recruitment-thatjobotlife-activity-6856254170513723392-W9dR",
      "confidence": 0.9,
      "distilled_content": "The source is a LinkedIn post by Scott Filbin, who is the Senior Director of Recruiting at Jobot. The post celebrates Ellina Oganyan for her achievements, specifically for reaching the Platinum 2 Bonus tier and being promoted to Executive Manager. Scott praises Ellina for her leadership qualities, kindness, and commitment to her team, indicating that she embodies the values sought in a manager. This post is relevant to Ellina Oganyan as it highlights her professional accomplishments and recognition within her organization, showcasing her growth and the support she receives from her colleagues."
    },
    {
      "index": 5,
      "url": "https://rocketreach.co/lunar-energy-hr-department_b7f61f5bc2af8565",
      "confidence": 0.9,
      "distilled_content": "The raw content is from the HR department section of Lunar Energy's website, detailing the structure and personnel within the department. Ellina Oganyan is identified as the Recruiting Manager at Lunar Energy, leading a team of five employees. The information highlights her role and seniority within the company, indicating her responsibilities in recruitment and human resources. This is relevant to Ellina Oganyan as it showcases her position and contributions to the organization, providing insight into her professional background and the team she manages."
    },
    {
      "index": 6,
      "url": "https://www.linkedin.com/posts/ellina-oganyan-68857113a_companyculture-employeeengagement-employeecare-activity-6891832542912241664-XuxF",
      "confidence": 0.7,
      "distilled_content": "The source is a LinkedIn post by Ellina Oganyan, who is identified as a Recruiting Manager. The post, dated two years ago, discusses initiatives by Caroo, a company focused on employee engagement and company culture. Ellina promotes two gift boxes designed for February: one for Black History Month, which supports Black-founded brands and donates a portion of proceeds to the Equal Justice Initiative, and another for Valentine's Day that includes team-building activities and supports Feeding America. This content is relevant to Ellina as it highlights her role in promoting employee care and engagement, aligning with her professional focus in human resources and leadership."
    },
    {
      "index": 7,
      "url": "https://www.linkedin.com/posts/ellina-oganyan-68857113a_happy-fathers-day-from-pacific-companies-activity-6413459653883232256-jo5_",
      "confidence": 0.7,
      "distilled_content": "The source is a LinkedIn post by Ellina Oganyan, who is identified as a Recruiting Manager at Pacific Companies. The post, dated six years ago, highlights a Father's Day initiative at Pacific Companies, where the team shared stories about their fathers and reflected on the importance of family. This post is relevant to Ellina as it showcases her role in fostering a positive workplace culture and emphasizes her connection to the company's values of teamwork and appreciation for family. The post also includes hashtags related to physician recruitment and teamwork, indicating her professional focus."
    },
    {
      "index": 8,
      "url": "https://www.linkedin.com/posts/ellina-oganyan-68857113a_10-reasons-why-you-should-stop-by-the-pacific-activity-6392417948920872960-3WVt",
      "confidence": 0.7,
      "distilled_content": "The source is a LinkedIn post by Ellina Oganyan, who is identified as a Recruiting Manager. The post, dated six years ago, discusses the reasons to visit the Pacific Companies booth at the ASPR event, indicating her involvement in recruitment and possibly in promoting her company at industry events. The post has garnered attention with likes and comments, showcasing her engagement with the professional community. This information is relevant as it highlights her professional role, her company's presence in the industry, and her active participation in networking opportunities."
    },
    {
      "index": 9,
      "url": "https://contactout.com/Ellina-Oganyan-34181609",
      "confidence": 0.6,
      "distilled_content": "Ellina Oganyan is a Recruitment Consultant at The Recruitment Depot, based in Orange County, California. She has held various roles in the staffing and recruiting industry, including positions as a Recruitment Advisor at HappyPath, Talent Acquisition Manager at Caroo, and several roles at Jobot, where she progressed from Senior Recruiter to Executive Manager. Her career in recruitment began in 2017, and she has a Bachelor's degree from California State University-Fullerton. The source provides her contact information, including her email address (eoganyan@lunarenergy.com) and phone number, making it relevant for networking or recruitment purposes."
    },
    {
      "index": 10,
      "url": "https://www.linkedin.com/posts/ellina-oganyan-68857113a_locumtenens-activity-6425852899708010496-LQFa",
      "confidence": 0.6,
      "distilled_content": "The source is a LinkedIn post by Ellina Oganyan, who is identified as a Recruiting Manager. The post is dated six years ago and includes a comment from another user, Andrea A., indicating a hiring opportunity. Ellina has a significant following on LinkedIn, with 6,357 followers and has made 14 posts. This information highlights her professional presence on LinkedIn, suggesting she is active in the recruiting field and potentially involved in job placements or networking within her industry. The context of the post indicates her engagement with hiring trends and her role in connecting talent with opportunities."
    }
  ]
    }

    # Make the POST request
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Print the response in a formatted way
        print("Status Code:", response.status_code)
        print("\nResponse:")
        print(response.json())
        print(response.text)  # Since this endpoint returns a string, not JSON
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    test_reachout()

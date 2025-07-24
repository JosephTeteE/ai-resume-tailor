# config.py
"""
Configuration module containing master resume data structure.
All sensitive personal data is loaded from environment variables.
"""

import os

MASTER_RESUME_DATA = {
    "CONTACT_INFO": {
        # Contact information loaded from environment variables
        "name": os.getenv("RESUME_NAME"),
        "details": f"{os.getenv('RESUME_CITY')}, {os.getenv('RESUME_STATE')} {os.getenv('RESUME_ZIP')} • {os.getenv('RESUME_PHONE')} • {os.getenv('RESUME_EMAIL')}"
    },
    "EDUCATION": [
        {
            "institution": "University of North Texas",
            "location": "Denton, Texas",
            "degree": "Master of Advanced Data Analytics (Part-time)",
            "dates": "Graduation Expected: Dec 2026",
            "courses": "Relevant Courses: Data Visualization, Prescriptive Analytics, Predictive Analytics"
        },
        {
            "institution": "Covenant University",
            "location": "Ogun, Nigeria",
            "degree": "B.S in Petroleum Engineering",
            "dates": "July 2019",
            "courses": "Relevant Course: Leadership Development and Project Management"
        }
    ],
    "RELEVANT_EXPERIENCE_STATIC": {
        "Conduent": {
            "location": "Remote",
            "dates": "Nov 2024 – Present",
            "original_bullets": [
                "Designed and deployed interactive Power BI dashboards to track document processing performance and operational KPIs.",
                "Extracted and analyzed structured data using SQL to identify error trends and validate document workflows.",
                "Performed trend and gap analysis on over 10,000+ document records to optimize workload distribution.",
                "Collaborated with IT and operations teams to automate weekly and monthly reporting processes."
            ]
        },
        "Itech Data Consulting": {
            "location": "Frederick, Maryland",
            "dates": "Sep 2022 – Oct 2024",
             "original_bullets": [
                "Translated business needs into functional requirements and detailed user stories.",
                "Designed and maintained real-time Power BI dashboards to track KPIs and business performance across teams.",
                "Streamlined reporting processes by 40% through automation of SQL queries."
            ]
        },
        "Mangrove & Partners Ltd": {
            "location": "Abuja, Nigeria",
            "dates": "Jan 2020 – Aug 2022",
             "original_bullets": [
                "Led workshops with business stakeholders to identify and address key business challenges.",
                "Developed and maintained Power BI dashboards to visualize operational and financial KPIs.",
                "Conducted data analysis that resulted in a 15% reduction in operational costs.",
                "Managed project schedules and budgets to ensure on-time delivery."
            ]
        }
    },
    "AWARD": "Certificate of Service – Program Chair for the Society of Petroleum Engineers (Covenant Chapter, 2019)",
    "ORGANIZATIONS": {
        "role": "Society of Petroleum Engineers, Covenant University, Program Chair",
        "dates": "June 2018 - July 2019"
    }
}
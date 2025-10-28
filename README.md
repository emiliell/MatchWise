# MatchWise: Resume-Job Matching Platform

MatchWise provides an interface for companies and candidates for matching resume and job description through NLP techniques.

## Features

### Main Menu

- Navigate to different sections like registration, login, and access multiple articles.

![Landing Page](images/LandingPage.png)

### User Authentication

- Registration for candidate and company
- Login

![Registration Page](images/RegistrationPage.png)



  
### For Candidates

- **Resume Upload:**

  - After logging in, candidates can easily upload their resumes in PDF format.
  
  ![Upload Resume](images/Resume upload page.png)

- **Job description to match:**

  - Candidate paste a job description to be matched. Select one of their resumes from the drop-down menu.
  
  ![Compare Resume and job description](images/ComparisonPage.png)

- **Matching Results:**

  - Skills, similarity score and success rate displayed.
  
  ![Results of resume and job description comparison](images/CandidateView_ComparisonResult.png)



### For Companies

- **Job Description Entry:**
  - Companies can enter job descriptions to find the best matching resumes after logging in.
  ![Upload job description](images/CompanyView_JobDescription.png)

- **Resume Matching:**
  - The system extracts technical keywords from job descriptions, matching them with skills listed in candidates' resumes stored in MongoDB. Candidates with the highest overlap of skills are listed in descending order. Companies can then view and download the resumes of matched candidates.

**Example**

- User with most overlap of skills is listed first.

  ![Top Candidates list](images/CompanyView_Results.png)



## Tech Stack
- **Back-End:**
  - Flask: Python-based micro web framework used to serve the application.
  - MongoDB: NoSQL database used to store user data and resumes.
  - SpaCy: Library for advanced Natural Language Processing used to fine tune current base model so that it can extract keywords from job descriptions.

- **Front-End:**
  - HTML: Markup language used for structuring and presenting content.
  - CSS: Style-sheet language used for describing the look and formatting of the document.

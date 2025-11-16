import spacy
from spacy.tokens import DocBin

# -----------------------------
# 1. Training Data
# -----------------------------
train_data = [
    ("Looking for a skilled Java developer with expertise in Spring and Hibernate frameworks.", {"entities": [(22, 36, "TECH"), (55, 61, "TECH"), (66, 75, "TECH")]}),
    ("We need a Front-end Developer proficient in React.js, HTML, and CSS.", {"entities": [(10, 29, "TECH"), (44, 52, "TECH"), (54, 58, "TECH"), (64, 67, "TECH")]}),
    ("Hiring a Full-stack developer with experience in Node.js, Express.js, MongoDB, and Angular.", {"entities": [(9, 29, "TECH"), (49, 56, "TECH"), (58, 68, "TECH"), (70, 77, "TECH"), (83, 90, "TECH")]}),
    ("Looking for a Python Developer with Django and Flask experience.", {"entities": [(14, 30, "TECH"), (36, 42, "TECH"), (47, 52, "TECH")]}),
    ("Seeking a proficient C++ developer familiar with Qt and Boost libraries.", {"entities": [(21, 24, "TECH"), (49, 51, "TECH"), (56, 61, "TECH")]}),
    ("Hiring a .NET developer with experience in C# and ASP.NET.", {"entities": [(9, 13, "TECH"), (43, 45, "TECH"), (50, 57, "TECH")]}),
    ("In search of a developer skilled in Ruby and Rails for web development projects.", {"entities": [(14, 23, "TECH"), (36, 40, "TECH"), (45, 50, "TECH"), (55, 70, "TECH")]}),
    ("We require an expert in cloud computing, familiar with AWS and Azure services.", {"entities": [(25, 30, "TECH"), (55, 58, "TECH"), (63, 68, "TECH")]}),
    ("Database Administrator with experience in SQL, Oracle, and Microsoft SQL Server.", {"entities": [(0, 23, "TECH"), (42, 45, "TECH"), (47, 53, "TECH"), (59, 79, "TECH")]}),
    ("Mobile developer proficient in Swift, Kotlin, and React Native for iOS and Android development.", {"entities": [(0, 17, "TECH"), (31, 36, "TECH"), (38, 44, "TECH"), (50, 62, "TECH")]}),
    ("Experienced data scientist with proficiency in R, Python, and TensorFlow.", {"entities": [(12, 27, "TECH"), (47, 48, "TECH"), (50, 56, "TECH"), (62, 72, "TECH")]}),
    ("Seeking software engineer with expertise in Go and Docker for backend systems.", {"entities": [(8, 25, "TECH"), (44, 46, "TECH"), (51, 57, "TECH"), (62, 69, "TECH")]}),
    ("Looking for a developer with experience in PHP and Laravel framework.", {"entities": [(14, 23, "TECH"), (43, 46, "TECH"), (51, 58, "TECH"), (59, 68, "TECH")]}),
    ("Hiring for a position that requires knowledge in Salesforce and Apex programming.", {"entities": [(49, 59, "TECH"), (64, 68, "TECH"), (69, 80, "TECH")]}),
    ("Need a developer familiar with JavaScript, TypeScript, and Vue.js for front-end development.", {"entities": [(7, 16, "TECH"), (31, 41, "TECH"), (43, 53, "TECH"), (59, 65, "TECH"), (71, 80, "TECH"), (81, 92, "TECH")]}),
    ("Senior DevOps engineer with experience in Jenkins, Docker, and Kubernetes.", {"entities": [(7, 13, "TECH"), (42, 49, "TECH"), (51, 57, "TECH"), (63, 73, "TECH")]}),
    ("Backend Developer experienced with Python, Flask, and PostgreSQL needed.", {"entities": [(0, 7, "TECH"), (35, 41, "TECH"), (43, 48, "TECH"), (54, 64, "TECH")]}),
    ("Front-end specialist with deep knowledge in React and Redux.", {"entities": [(0, 28, "TECH"), (44, 49, "TECH"), (54, 59, "TECH")]}),
    ("The candidate should be proficient in Adobe Photoshop and Illustrator for graphic design.", {"entities": [(44, 53, "TECH"), (58, 69, "TECH")]}),
    ("Java developer with experience in Spring Boot and Microservices architecture.", {"entities": [(0, 4, "TECH"), (34, 45, "TECH"), (64, 76, "TECH")]}),
    ("Seeking a Data Scientist proficient in Python, R, and machine learning libraries like TensorFlow and PyTorch.", {"entities": [(10, 24, "TECH"), (39, 45, "TECH"), (47, 48, "TECH"), (54, 70, "TECH"), (86, 96, "TECH"), (101, 108, "TECH")]}),
    ("Mobile Application Developer with proficiency in Swift and Objective-C.", {"entities": [(0, 6, "TECH"), (49, 54, "TECH"), (59, 69, "TECH")]}),
    ("Web Developer with proficiency in HTML, CSS, JavaScript and experience with Angular and React.", {"entities": [(0, 13, "TECH"), (34, 38, "TECH"), (40, 43, "TECH"), (45, 55, "TECH"), (76, 83, "TECH"), (88, 93, "TECH")]}),
    ("Cloud Engineer experienced in AWS, Google Cloud Platform, and Azure.", {"entities": [(0, 14, "TECH"), (35, 47, "TECH"), (62, 67, "TECH")]}),
    ("Seeking an expert in database technologies like MySQL, MongoDB, and Oracle.", {"entities": [(21, 29, "TECH"), (48, 53, "TECH"), (55, 62, "TECH"), (68, 74, "TECH")]}),
    ("Experienced system administrator knowledgeable in Linux, Windows Server, and networking.", {"entities": [(12, 32, "TECH"), (50, 55, "TECH"), (57, 71, "TECH"), (77, 87, "TECH")]}),
    ("Rust Developer skilled in writing high-performance systems with Tokio and Actix.", {"entities": [(0, 14, "TECH"), (36, 41, "TECH"), (46, 51, "TECH"), (52, 68, "TECH")]}),
    ("Flutter Engineer experienced in building cross-platform mobile apps with Dart.", {"entities": [(0, 16, "TECH"), (36, 42, "TECH"), (73, 77, "TECH"), (43, 73, "TECH")]}),
    ("Data Engineer proficient in Apache Spark, Hadoop, and Kafka for big data pipelines.", {"entities": [(0, 13, "TECH"), (33, 44, "TECH"), (46, 52, "TECH"), (58, 63, "TECH"), (68, 88, "TECH")]}),
    ("AI Researcher with expertise in PyTorch Lightning, Hugging Face Transformers, and NLP models.", {"entities": [(0, 11, "TECH"), (32, 53, "TECH"), (55, 79, "TECH"), (85, 88, "TECH")]}),
    ("Site Reliability Engineer familiar with Prometheus, Grafana, and ELK stack for monitoring.", {"entities": [(0, 24, "TECH"), (40, 50, "TECH"), (52, 59, "TECH"), (65, 74, "TECH"), (79, 89, "TECH")]}),
    ("Machine Learning Engineer experienced in Scikit-learn, XGBoost, and LightGBM for predictive modeling.", {"entities": [(0, 25, "TECH"), (44, 55, "TECH"), (57, 63, "TECH"), (69, 76, "TECH"), (81, 102, "TECH")]}),
    ("DevOps Architect skilled in Kubernetes, Docker Swarm, and Helm for orchestration.", {"entities": [(0, 17, "TECH"), (32, 42, "TECH"), (44, 55, "TECH"), (61, 65, "TECH"), (70, 84, "TECH")]}),
    ("Game Developer proficient in Unity, Unreal Engine, and C# for 3D simulation projects.", {"entities": [(0, 14, "TECH"), (36, 41, "TECH"), (43, 55, "TECH"), (61, 63, "TECH"), (68, 92, "TECH")]}),
    ("Backend Engineer experienced with GraphQL, REST APIs, and gRPC for scalable microservices.", {"entities": [(0, 15, "TECH"), (36, 43, "TECH"), (45, 53, "TECH"), (59, 63, "TECH"), (68, 92, "TECH")]}),
    ("IoT Developer familiar with MQTT, Raspberry Pi, and Arduino for connected devices.", {"entities": [(0, 13, "TECH"), (31, 35, "TECH"), (37, 48, "TECH"), (54, 61, "TECH"), (66, 82, "TECH")]}),
    ("Cybersecurity Analyst skilled in Nessus, Wireshark, and Metasploit for vulnerability assessment.", {"entities": [(0, 21, "TECH"), (32, 38, "TECH"), (40, 49, "TECH"), (55, 64, "TECH"), (69, 96, "TECH")]}),
    ("Big Data Engineer proficient in Elasticsearch, Hadoop, and Cassandra for analytical workloads.", {"entities": [(0, 17, "TECH"), (36, 49, "TECH"), (51, 57, "TECH"), (63, 72, "TECH"), (77, 100, "TECH")]}),
    ("QA Automation Engineer skilled in Selenium, Cypress, and Appium for test automation frameworks.", {"entities": [(0, 25, "TECH"), (36, 44, "TECH"), (46, 52, "TECH"), (58, 64, "TECH"), (69, 97, "TECH")]}),
    ("Cloud Solutions Architect experienced in OpenStack, VMware, and AWS for enterprise infrastructure.", {"entities": [(0, 25, "TECH"), (41, 50, "TECH"), (52, 58, "TECH"), (64, 67, "TECH"), (72, 97, "TECH")]}),
    ("Augmented Reality Developer proficient in ARKit, ARCore, and Vuforia for immersive mobile experiences.", {"entities": [(0, 28, "TECH"), (41, 46, "TECH"), (48, 54, "TECH"), (60, 67, "TECH"), (72, 104, "TECH")]}),
    ("Big Data Architect experienced in Apache Flink, Presto, and Druid for streaming analytics.", {"entities": [(0, 21, "TECH"), (39, 50, "TECH"), (52, 58, "TECH"), (64, 69, "TECH"), (74, 92, "TECH")]}),
    ("Data Visualization Specialist proficient in Tableau, Power BI, and Looker for business insights.", {"entities": [(0, 30, "TECH"), (44, 51, "TECH"), (53, 60, "TECH"), (66, 72, "TECH"), (77, 94, "TECH")]}),
    ("Full-Stack JavaScript Developer proficient in Node.js, Express, and Next.js for modern web apps.", {"entities": [(0, 32, "TECH"), (47, 54, "TECH"), (56, 63, "TECH"), (69, 76, "TECH"), (81, 95, "TECH")]}),
]

# -----------------------------
# 2. Load English Language Model
# -----------------------------
nlp = spacy.load("en_core_web_sm") 
ner = nlp.get_pipe("ner")

ner.add_label("TECH")

# -----------------------------
# 3. Create DocBin
# -----------------------------
db = DocBin()
for text, annotations in train_data:
    doc = nlp.make_doc(text)
    ents = []
    for start, end, label in annotations["entities"]:
        span = doc.char_span(start, end, label=label)
        if span is None:
            print(f"Skipped invalid span in: '{text[start:end]}'")  # debug info
            continue
        if not any(ch.isalnum() for ch in span.text):
            continue  # skip punctuation-only entities
        ents.append(span)
    doc.ents = ents
    db.add(doc)

db.to_disk("./train.spacy")
print("✅ Saved cleaned training data to train.spacy")

# -----------------------------
# 4. Train Model
# -----------------------------
optimizer = nlp.initialize()
for epoch in range(25):
    losses = {}
    for text, annotations in train_data:
        doc = nlp.make_doc(text)
        example = spacy.training.Example.from_dict(doc, annotations)
        nlp.update([example], drop=0.2, sgd=optimizer, losses=losses)
    print(f"Epoch {epoch+1:02d} | Losses: {losses}")

nlp.to_disk("model_upgrade")

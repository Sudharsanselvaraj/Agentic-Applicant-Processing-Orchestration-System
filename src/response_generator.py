import re

R1_QUESTIONS = {
    "approach": "What is your first approach to solve this problem?",
    "tools": "What tools and technologies would you use?",
    "experience": "Tell us about a project you've built.",
    "motivation": "Why do you want to join GenoTek?"
}

R2_QUESTIONS = {
    "code_review": "Can you show us a code sample related to your approach?",
    "deep_dive": "Can you explain your solution in more detail?",
    "challenge": "What was the hardest technical challenge you've faced?"
}

def generate_r1_email(candidate_name, candidate_skills, position="AI Agent Developer"):
    subject = f"Application Status - {position} at GenoTek"
    
    body = f"""Hi {candidate_name},

Thank you for applying to the {position} role at GenoTek.

Based on your application, your profile looks promising. We'd like to learn more about you.

Question 1: What is your first approach to solve web automation challenges where no official API exists?

Question 2: Tell us about a project where you built something from scratch.

Please reply with your answers. There are no right or wrong answers - we're looking for your genuine thinking.

Best regards,
GenoTek HR Team
"""
    return subject, body

def determine_round_context(previous_responses):
    if not previous_responses:
        return "r1"
    
    round_num = len(previous_responses) + 1
    if round_num == 2:
        return "r2"
    elif round_num == 3:
        return "r3"
    return "followup"

def analyze_response_for_context(response_text):
    context = {}
    
    tech_keywords = ['selenium', 'playwright', 'python', 'javascript', 'api', 'scraping', 'automation', 'webdriver', 'beautiful soup', 'requests', 'rest', 'http']
    found_tech = [kw for kw in tech_keywords if kw in response_text.lower()]
    context['technologies_mentioned'] = found_tech
    
    if any(word in response_text.lower() for word in ['i built', 'i created', 'i made', 'i developed']):
        context['has_project'] = True
    
    if len(response_text.split()) > 100:
        context['response_length'] = 'detailed'
    elif len(response_text.split()) > 30:
        context['response_length'] = 'moderate'
    else:
        context['response_length'] = 'short'
    
    if '?' in response_text:
        context['asks_questions'] = True
    
    return context

def generate_followup_email(candidate_name, previous_responses, candidate_context=None):
    last_response = previous_responses[-1] if previous_responses else ""
    context = analyze_response_for_context(last_response)
    
    subject = f"Re: Your Application to GenoTek"
    
    if context.get('asks_questions'):
        body = f"""Hi {candidate_name},

Thanks for your response - great question!

To answer your question: In our experience, the best approach combines understanding the underlying HTTP requests (using browser DevTools) with automation tools. We'd love to hear more about your specific approach.

Can you share a code example or explain your technical approach in more detail?

Best,
GenoTek HR
"""
    elif context.get('response_length') == 'short':
        body = f"""Hi {candidate_name},

Thank you for replying! We'd love to hear more about your experience.

Could you tell us more about a project you've worked on? Specifically, what challenge did you solve and how did you approach it?

Best,
GenoTek HR
"""
    elif len(context.get('technologies_mentioned', [])) > 0:
        tech = context['technologies_mentioned'][0]
        body = f"""Hi {candidate_name},

Interesting that you mentioned {tech}. We'd like to learn more.

Can you explain how you've used {tech} in a real project? What was the problem you solved?

Best,
GenoTek HR
"""
    else:
        body = f"""Hi {candidate_name},

Thank you for your response! We have one more question:

Can you describe a technical challenge you faced and how you solved it?

Best,
GenoTek HR
"""
    
    return subject, body

def extract_email_from_header(header):
    match = re.search(r'<(.+?)>', header)
    if match:
        return match.group(1)
    return header.strip()

def parse_candidate_reply(email_body, email_from):
    email = extract_email_from_header(email_from)
    return {
        'email': email,
        'body': email_body,
        'timestamp': None
    }
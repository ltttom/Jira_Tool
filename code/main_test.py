import pandas as pd
import re
import os
import argparse

class Issue:
    def __init__(self, jira_id, assignee, summary, fix_version=None, status=None, description=None):
        self.jira_id = jira_id
        self.assignee = assignee
        self.summary = summary
        self.fix_version = fix_version
        self.status = status
        self.description = description

class List1:
    def __init__(self):
        self.issues = {}

    def parse_git_log(self, filepath):
        with open(filepath, 'r') as file:
            for line in file:
                commit_hash, author, message = line.strip().split('\t', 2)
                
                jira_ids = re.findall(r'\b[A-Z]+-\d+\b', message)
                
                for jira_id in jira_ids:
                    if jira_id not in self.issues:
                        self.issues[jira_id] = Issue(jira_id, author, message)

    def get_issues(self):
        return self.issues.values()

class List2:
    def __init__(self):
        self.issues = []

    def parse_jira_export(self, filepath):

        tables = pd.read_html(filepath, header = 0)
        if not tables:
            raise ValueError("No tables found in the HTML file")
        
        df = tables[1]
        required_columns = ['Key', 'Summary', 'Assignee', 'Fix Version/s', 'Status', 'Description']
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError("The input file does not have the required columns.")
        
        for _, row in df.iterrows():
            issue = Issue(
                jira_id=row['Key'],
                assignee=row['Assignee'],
                summary=row['Summary'],
                fix_version=row['Fix Version/s'],
                status=row['Status'],
                description=row['Description']
            )
            self.issues.append(issue)

    def get_issues(self):
        return self.issues

def extract_version(input_file):
    match = re.search(r'(\d+\.\d+\.\d+)', input_file)
    return match.group(1) if match else 'unknown_version'

def generate_output_filename(input_file, suffix, extension):
    version = extract_version(input_file)
    return f"{version}_{suffix}.{extension}"

def issues_Notfound_Notsolved(list1, list2, output_file):
    
    list2_issues = {issue.jira_id: issue.status for issue in list2.get_issues()}
    
    issues_to_export = []
    
    for issue in list1.get_issues():
        if issue.jira_id not in list2_issues:
            issues_to_export.append({
                'Jira ID': issue.jira_id,
                'Assignee': issue.assignee,
                'Summary': issue.summary,
                'Status': 'Not found'
            })
        else:
            list2_status = list2_issues[issue.jira_id]
            if list2_status.lower() not in ['resolved', 'closed']:
                issues_to_export.append({
                    'Jira ID': issue.jira_id,
                    'Assignee': issue.assignee,
                    'Summary': issue.summary,
                    'Status': list2_status
                })
    

    df = pd.DataFrame(issues_to_export)

    output_folder = 'output'
    os.makedirs(output_folder, exist_ok=True)
    full_path = os.path.join(output_folder, output_file)

    df.to_excel(full_path, index=False)

    
    print(f"Exported {len(issues_to_export)} issues to {full_path}")


def issues_missing_Description(list2, output_file):

    keywords = {"description", "solution", "cause", "test"}

    issues_to_export = []

    for issue in list2.get_issues():
        if not isinstance(issue.description, str) or not issue.description:  
            # print(f"Found issue with no description: {issue.jira_id}")
            issues_to_export.append({
                'Jira ID': issue.jira_id,
                'Assignee': issue.assignee,
                'Summary': issue.summary,
                'Fix Version': issue.fix_version,
                'Status': issue.status,
                'Description': issue.description,
                'Status Message': 'No description'
            })
        elif isinstance(issue.description, str) and issue.description:
            description_lower = issue.description.lower()
            missing_keywords = keywords - set(word for word in description_lower.split())
            if missing_keywords:
                issues_to_export.append({
                    'Jira ID': issue.jira_id,
                    'Assignee': issue.assignee,
                    'Summary': issue.summary,
                    'Fix Version': issue.fix_version,
                    'Status': issue.status,
                    'Description': issue.description,
                    'Status Message': f"ERROR: missing {missing_keywords}"
                })
    
    df = pd.DataFrame(issues_to_export)

    output_folder = 'output'
    os.makedirs(output_folder, exist_ok=True)
    full_path = os.path.join(output_folder, output_file)

    df.to_excel(full_path, index=False)

    print(f"Exported {len(issues_to_export)} issues to {full_path}")

def issues_saved_txt(list2, output_file):
    
    output_folder = 'output'
    os.makedirs(output_folder, exist_ok=True)
    full_path = os.path.join(output_folder, output_file)
    
    with open(full_path, 'w') as file:
        for issue in list2.get_issues():
            file.write(f"{issue.jira_id}-{issue.summary}\n")
    
    print(f"Exported issues to {full_path}")



def main():
    parser = argparse.ArgumentParser(description="Process Git log and Jira export files")
    parser.add_argument('-g', '--gitlog', type=str, required=True, help="Path to the Git log file")
    parser.add_argument('-j', '--jira', type=str, required=True, help="Path to the Jira export file")
    
    args = parser.parse_args()
    
    list1 = List1()
    list1.parse_git_log(args.gitlog)
    
    list2 = List2()
    list2.parse_jira_export(args.jira)

    notfound_notsolved_output = generate_output_filename(args.gitlog, 'Notfound_Notsolved', 'xlsx')
    missing_description_output = generate_output_filename(args.jira, 'Missing_Description', 'xlsx')
    saved_txt_output = generate_output_filename(args.jira, 'Text_file', 'txt')
    
    issues_Notfound_Notsolved(list1, list2, notfound_notsolved_output)
    issues_missing_Description(list2, missing_description_output)
    issues_saved_txt(list2, saved_txt_output)

if __name__ == "__main__":
    main()
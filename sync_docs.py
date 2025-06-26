# Python script to synchronize markdown documents from multiple GitHub repositories
# for the md-toc project.

import yaml
import os
import sys
import shutil
import re # For title generation
from git import Repo, GitCommandError, InvalidGitRepositoryError

CONFIG_FILE = "sources.yaml"
DEFAULT_CACHE_DIR = ".doc_cache"

# --- Helper to list directory contents (can be removed or kept for debugging) ---
def list_directory_contents(path_to_list: str):
    # print(f"--- Listing contents of: {path_to_list} ---") # Usually commented out
    if not os.path.exists(path_to_list):
        # print(f"Directory does not exist: {path_to_list}")
        return
    if not os.path.isdir(path_to_list):
        # print(f"Not a directory: {path_to_list}")
        return
    # try:
    #     for item in os.listdir(path_to_list):
    #         item_path = os.path.join(path_to_list, item)
    #         if os.path.isdir(item_path):
    #             print(f"  {item}/")
    #         else:
    #             print(f"  {item}")
    # except Exception as e:
    #     print(f"Error listing directory {path_to_list}: {e}")
    # print(f"--- End of listing for: {path_to_list} ---")
    pass # Keep it silent unless actively debugging paths

# --- Configuration Loading and Validation (unchanged) ---
def load_config(config_path: str) -> dict | None:
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return None
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        # print(f"Configuration loaded successfully from '{config_path}'.") # Quieter
        return config
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading config: {e}")
        return None

def validate_config(config: dict) -> bool:
    if not isinstance(config, dict): print("Error: Config root should be a dictionary."); return False
    if "processed_docs_root" not in config or not isinstance(config["processed_docs_root"], str):
        print("Error: 'processed_docs_root' missing or not a string."); return False
    if "sources" not in config or not isinstance(config["sources"], list):
        print("Error: 'sources' missing or not a list."); return False
    for i, source in enumerate(config["sources"]):
        if not isinstance(source, dict): print(f"Error: Source at index {i} not a dictionary."); return False
        keys = ["id", "name", "repo_url", "branch", "documents"]
        if not all(key in source for key in keys):
            print(f"Error: Source '{source.get('id', 'Unknown')}' missing keys."); return False
        if "default_front_matter" in source and not isinstance(source["default_front_matter"], dict):
            print(f"Error: 'default_front_matter' in source '{source['id']}' must be a dict."); return False
        if not isinstance(source["documents"], list) or not source["documents"]:
            print(f"Error: 'documents' in source '{source['id']}' must be non-empty list."); return False
        for j, doc_set in enumerate(source["documents"]):
            if not isinstance(doc_set, dict): print(f"Error: Doc set {j} for '{source['id']}' not dict."); return False
            doc_keys = ["target_dir", "base_repo_path", "markdown_files", "image_dirs"]
            if not all(key in doc_set for key in doc_keys):
                print(f"Error: Doc set for '{source['id']}' missing keys."); return False
            if not isinstance(doc_set["markdown_files"], list):
                print(f"Error: 'markdown_files' for '{source['id']}' must be list."); return False
            if not isinstance(doc_set["image_dirs"], list):
                print(f"Error: 'image_dirs' for '{source['id']}' must be list."); return False
    # print("Configuration validation passed.") # Quieter
    return True
# --- End Configuration Loading and Validation ---


# --- Git Repository Handling (unchanged) ---
def get_source_repo(repo_url: str, branch: str, cache_base_dir: str, repo_id: str) -> Repo | None:
    local_repo_path = os.path.join(cache_base_dir, repo_id)
    repo = None
    try:
        if os.path.exists(local_repo_path):
            # print(f"Repository '{repo_id}' found at '{local_repo_path}'. Fetching updates...") # Quieter
            try:
                repo = Repo(local_repo_path)
                # print(f"Fetching origin for '{repo_id}'...") # Quieter
                repo.remotes.origin.fetch(prune=True)
                # print(f"Checking out branch/tag '{branch}' for '{repo_id}'...") # Quieter
                repo.git.checkout(branch)
                if not repo.head.is_detached:
                    # print(f"Pulling latest changes for branch '{branch}' in '{repo_id}'...") # Quieter
                    current_branch_obj = repo.active_branch
                    if current_branch_obj.tracking_branch():
                        repo.remotes.origin.pull()
                        # print(f"Successfully pulled updates for '{repo_id}'.") # Quieter
                    else:
                        # print(f"Branch '{branch}' in '{repo_id}' is not tracking. Resetting to origin/{branch}.") # Quieter
                        repo.git.reset(f"origin/{branch}", hard=True)
                        # print(f"Successfully reset '{repo_id}' to 'origin/{branch}'.") # Quieter
                # else:
                    # print(f"HEAD is detached for '{repo_id}' ({branch}). Skipping pull.") # Quieter
            except InvalidGitRepositoryError:
                print(f"Error: '{local_repo_path}' not valid Git repo. Removing and re-cloning.")
                shutil.rmtree(local_repo_path); repo = None
            except GitCommandError as e:
                print(f"Git command error for existing repo '{repo_id}': {e}"); return None
        if repo is None:
            print(f"Cloning repository '{repo_id}' from '{repo_url}' to '{local_repo_path}' (branch: {branch})...")
            try:
                repo = Repo.clone_from(repo_url, local_repo_path, branch=branch)
                # print(f"Successfully cloned '{repo_id}' and checked out '{branch}'.") # Quieter
            except GitCommandError as e:
                print(f"Error cloning repo '{repo_id}': {e}")
                if os.path.exists(local_repo_path): shutil.rmtree(local_repo_path)
                return None
            except Exception as e:
                print(f"Unexpected error during clone of '{repo_id}': {e}")
                if os.path.exists(local_repo_path): shutil.rmtree(local_repo_path)
                return None
        if repo.head.is_detached:
            if branch in repo.tags:
                 if repo.head.commit != repo.tags[branch].commit:
                     print(f"Error: Tag '{branch}' commit mismatch for '{repo_id}'."); return None
            # elif not (repo.head.commit.hexsha.startswith(branch) or str(repo.head.commit) == branch) :
                 # print(f"Warning: Detached HEAD at unexpected commit for '{repo_id}' when '{branch}' specified.")
        elif str(repo.active_branch) != branch:
            print(f"Warning: Active branch '{repo.active_branch}', expected '{branch}'. Checkout again.")
            try:
                repo.git.checkout(branch)
                if str(repo.active_branch) != branch:
                    print(f"Critical: Could not ensure branch '{branch}' for '{repo_id}'."); return None
            except GitCommandError as e:
                print(f"Error during final checkout of '{branch}' for '{repo_id}': {e}"); return None
        list_directory_contents(local_repo_path) # Keep this for path debugging if necessary
        return repo
    except Exception as e:
        print(f"Unexpected error with repository '{repo_id}': {e}"); return None
# --- End Git Repository Handling ---

# --- File Processing ---
def generate_title_from_filename(filename: str) -> str:
    """Generates a title from a filename (e.g., 'file_name.md' -> 'File Name')."""
    base = os.path.splitext(filename)[0]
    return base.replace('_', ' ').replace('-', ' ').title()

def process_source_documents(source_config: dict, global_docs_root: str):
    repo_local_path = source_config.get('repo_local_path')
    if not repo_local_path:
        print(f"Error: Local repo path missing for '{source_config.get('id', 'Unknown')}'. Skip."); return False
    # print(f"Processing documents for source: {source_config['name']} ({source_config['id']})") # Quieter
    processed_docs = False
    default_fm = source_config.get("default_front_matter", {})

    for doc_set in source_config.get("documents", []):
        base_repo_path_segment = doc_set.get('base_repo_path', '')
        full_source_base_path = os.path.join(repo_local_path, base_repo_path_segment)
        target_dir_segment = doc_set.get('target_dir')
        if not target_dir_segment:
            print(f"Warning: 'target_dir' missing for '{source_config['id']}'. Skip set."); continue
        target_dir_segment = target_dir_segment.strip(os.sep)
        target_doc_set_dir = os.path.join(global_docs_root, target_dir_segment)
        try:
            os.makedirs(target_doc_set_dir, exist_ok=True)
            # print(f"Ensured target directory exists: {target_doc_set_dir}") # Quieter
        except OSError as e:
            print(f"Error creating dir '{target_doc_set_dir}': {e}. Skip set."); continue

        # print(f"  Processing doc set: target='{target_dir_segment}', source_base='{full_source_base_path}'") # Quieter
        list_directory_contents(full_source_base_path)

        for md_file_pattern in doc_set.get("markdown_files", []):
            source_file_path = os.path.join(full_source_base_path, md_file_pattern)
            target_file_name = md_file_pattern
            target_file_path = os.path.join(target_doc_set_dir, target_file_name)
            target_file_subdir = os.path.dirname(target_file_path)
            if not os.path.exists(target_file_subdir):
                try: os.makedirs(target_file_subdir, exist_ok=True)
                except OSError as e: print(f"Error creating sub-dir '{target_file_subdir}': {e}. Skip file."); continue

            if os.path.exists(source_file_path) and os.path.isfile(source_file_path):
                try:
                    with open(source_file_path, 'r', encoding='utf-8') as f_in:
                        content = f_in.read()

                    final_content = content
                    if not content.startswith("---"):
                        print(f"    Adding front matter to: '{target_file_path}'")
                        # Prepare new front matter
                        new_fm = {}
                        new_fm.update(default_fm) # Start with defaults from config
                        if 'title' not in new_fm: # Add title if not in defaults
                            new_fm['title'] = generate_title_from_filename(os.path.basename(md_file_pattern))

                        fm_lines = ["---"]
                        for key, value in new_fm.items():
                            fm_lines.append(f"{key}: {yaml.dump(value, default_flow_style=True).strip()}")
                        fm_lines.append("---")
                        fm_block = "\n".join(fm_lines) + "\n\n"
                        final_content = fm_block + content
                    else:
                        print(f"    Front matter already exists in: '{source_file_path}' (targeting '{target_file_path}')")

                    with open(target_file_path, 'w', encoding='utf-8') as f_out:
                        f_out.write(final_content)
                    # shutil.copystat(source_file_path, target_file_path) # Preserve original file stats like timestamps
                    print(f"    Processed: '{source_file_path}' -> '{target_file_path}'")
                    processed_docs = True
                except Exception as e:
                    print(f"    Error processing/writing file '{source_file_path}' to '{target_file_path}': {e}")
            else:
                print(f"    Warning: Source MD file not found: '{source_file_path}'")
    return processed_docs
# --- End File Processing ---

if __name__ == "__main__":
    print("Starting document synchronization process...")
    cache_dir = os.path.abspath(DEFAULT_CACHE_DIR)
    if not os.path.exists(cache_dir): os.makedirs(cache_dir); print(f"Created cache dir: {cache_dir}")

    config_data = load_config(CONFIG_FILE)
    if not config_data: print(f"Config '{CONFIG_FILE}' load failed. Exit."); sys.exit(1)

    print("Validating configuration...")
    if not validate_config(config_data): print("Config invalid. Check 'sources.yaml'. Exit."); sys.exit(1)
    else: print("Configuration is valid.")

    global_docs_output_root = config_data.get("processed_docs_root", "docs")
    if not os.path.isabs(global_docs_output_root):
        global_docs_output_root = os.path.abspath(global_docs_output_root)
    try:
        os.makedirs(global_docs_output_root, exist_ok=True)
        print(f"Ensured global output directory: {global_docs_output_root}")
    except OSError as e: print(f"Error creating output dir '{global_docs_output_root}': {e}. Exit."); sys.exit(1)

    print("\nProcessing source repositories...")
    any_repo_failed = False
    for source_idx, source in enumerate(config_data.get("sources", [])):
        repo_id = source.get("id"); repo_url = source.get("repo_url"); branch = source.get("branch")
        if not all([repo_id, repo_url, branch]):
            print(f"Skipping source #{source_idx} due to missing info."); any_repo_failed = True; continue

        print(f"\n--- Processing source: {source['name']} ({repo_id}) ---")
        repo_instance = get_source_repo(repo_url, branch, cache_dir, repo_id)
        if repo_instance:
            # print(f"Successfully prepared repo for '{repo_id}' at '{repo_instance.working_dir}'.") # Quieter
            source['repo_local_path'] = repo_instance.working_dir
            if not process_source_documents(source, global_docs_output_root):
                print(f"Warning: No documents processed for source '{repo_id}'.")
        else:
            print(f"Failed to prepare repository for '{repo_id}'. Skipping."); any_repo_failed = True

    if not any_repo_failed: print("\nAll source repositories prepared.")
    else: print("\nSome repositories failed. Check logs.")

    print(f"\n--- Contents of '{global_docs_output_root}' directory (Python os.walk): ---")
    try:
        for root, dirs, files in os.walk(global_docs_output_root):
            prefix = os.path.relpath(root, global_docs_output_root)
            if prefix == ".": prefix = ""
            for name in sorted(dirs): print(os.path.join(prefix, name) + "/")
            for name in sorted(files): print(os.path.join(prefix, name))
    except Exception as e: print(f"Error walking dir '{global_docs_output_root}': {e}")
    print("--- End of contents ---")

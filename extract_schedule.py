import json
import re
import requests
import os
import time

from pathlib import Path

from argparse import ArgumentParser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_activities(schedule_url = 'https://that.us/events/wi/2022/schedule/'):
	html_text = requests.get(schedule_url).text
	soup = BeautifulSoup(html_text, 'html.parser')
	activity_set = set()
	for link in soup.find_all('a'):
		link_url = link.get('href')
		if link_url is None:
			continue
		match = re.search('/activities/([^/]+)/?', link_url)
		if match and match.group(1) != "create":
			activity_set.add(link_url.strip())
	return activity_set

def main():
	parser = ArgumentParser()
	parser.add_argument("--cache-path", default=".cache", type=Path)
	parser.add_argument("--output-dir", default="build", type=Path)
	args = parser.parse_args()

	cache_valid = os.path.exists(args.cache_path / "activity_list.txt")

	if not cache_valid:
		os.makedirs(args.cache_path, exist_ok=True)

	activity_set = set()
	if cache_valid:
		with open(args.cache_path / "activity_list.txt", "r") as fp:
			for activity in fp:
				activity_set.add(activity.strip())
	
	latest_activities_set = get_activities()
	new_activities_set = latest_activities_set - activity_set
	
	if len(new_activities_set) > 0:
		print("New activities found, updating cache...")

		activity_set = latest_activities_set
		cache_valid = False

		with open(".cache/activity_list.txt", "w") as fp:
			for activity in activity_set:
				fp.write(f"{activity}\n")

	all_activities = []
	for activity in activity_set:
		activity_id = re.search('/activities/([^/]+)/?', activity).group(1)
		html_text = None
		if cache_valid and os.path.exists(f".cache/{activity_id}"):
				with open(f".cache/{activity_id}") as fp:
					html_text = fp.read()

		if html_text is None:
			activity_url = f'https://that.us/{activity}'
			print(f"Fetching {activity_url}")
			html_text = requests.get(activity_url).text

		if not cache_valid:
			with open(f".cache/{activity_id}", "w") as fp:
				fp.write(html_text)

		soup = BeautifulSoup(html_text, 'html.parser')

		title_element = soup.find("h2", class_="text-2xl")
		title = title_element.text

		date_element = title_element.next_sibling.next_sibling
		date = date_element.get_text().strip()
		try:
			lines = date.split("\n")
			if len(lines) == 7:
				date, duration, duration_2, _, _, _, _, = date.split("\n")
				location = "Online"
			elif len(lines) == 10:
				date, duration, duration_2, _, _, _, _, _, _, location = date.split("\n")
			else:
				raise Exception("unknown format!")
		except Exception as e:
			print("==============")
			print(date)
			print("==============")
			import sys
			sys.exit(1)

		# Wednesday, July 27, 2022 - 7:30 PM UTC
		start_time = datetime.strptime(date[:-5], '%A, %B %d, %Y - %I:%M %p %Z')
		assert "hour" in duration_2, f"{activity_id}: {duration} {duration_2}"
		end_time = start_time + timedelta(hours=float(duration))

		description_element = date_element.next_sibling.next_sibling.next_sibling.next_sibling
		description = description_element.get_text()

		activity_obj = {
			"title": title,
			"start_time": start_time.timestamp(),
			"end_time": end_time.timestamp(),
			"location": location,
			"description": description,
			"link": f'https://that.us/{activity}'
		}
		all_activities.append(activity_obj)
		print(activity_obj["title"])
		with open(f".cache/{activity_id}.json", "w") as fp:
			json.dump(activity_obj, fp)

	with open(f"schedule.json", "w") as fp:
			json.dump(all_activities, fp)

	# Get last updated date
	last_updated = time.strftime("%a, %d %b %Y %H:%M:%S %Z", 
		time.gmtime(os.path.getmtime(args.cache_path / "activity_list.txt"))
	)

	# Write html
	with open("template.html") as fp:
		html_template = fp.read()

	html_template = html_template.replace("<<<<SCHEDULE>>>>", json.dumps(all_activities))
	html_template = html_template.replace("<<<<LASTUPDATED>>>>", last_updated)

	os.makedirs(args.output_dir, exist_ok=True)
	with open(args.output_dir / "index.html", "w") as fp:
		fp.write(html_template)


if __name__ == '__main__':
	main()
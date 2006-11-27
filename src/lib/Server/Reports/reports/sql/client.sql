CREATE VIEW reports_current_interactions AS SELECT x.client_id AS client_id, reports_interaction.id AS interaction_id FROM (select client_id, MAX(timestamp) as timer FROM reports_interaction GROUP BY client_id) x, reports_interaction WHERE reports_interaction.client_id = x.client_id AND reports_interaction.timestamp = x.timer
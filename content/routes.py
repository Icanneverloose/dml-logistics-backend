from flask import Blueprint, request, jsonify, session
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.auth_utils import require_admin as check_admin
from .content_utils import (
    load_content, 
    get_section, 
    update_section, 
    create_section, 
    delete_section
)

content_bp = Blueprint('content_bp', __name__)

def require_admin():
    """Check if user is admin"""
    is_admin_user, _ = check_admin()
    return is_admin_user

@content_bp.route('/api/content', methods=['GET'])
def get_all_content():
    """Get all content blocks"""
    try:
        content = load_content()
        return jsonify({
            'success': True,
            'content': content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading content: {str(e)}'
        }), 500

@content_bp.route('/api/content/<section>', methods=['GET'])
def get_section_content(section):
    """Get specific section content"""
    try:
        section_data = get_section(section)
        if section_data:
            return jsonify({
                'success': True,
                'content': section_data
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Section "{section}" not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading section: {str(e)}'
        }), 500

@content_bp.route('/api/content/<section>', methods=['PUT'])
def update_section_content(section):
    """Update specific section content"""
    if not require_admin():
        return jsonify({
            'success': False,
            'message': 'Admin access required'
        }), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Ensure section name is included
        data['section'] = section
        
        success = update_section(section, data)
        if success:
            return jsonify({
                'success': True,
                'message': f'Section "{section}" updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Section "{section}" not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating section: {str(e)}'
        }), 500

@content_bp.route('/api/content', methods=['POST'])
def create_new_section():
    """Create new section"""
    if not require_admin():
        return jsonify({
            'success': False,
            'message': 'Admin access required'
        }), 403
    
    try:
        data = request.get_json()
        if not data or 'section' not in data:
            return jsonify({
                'success': False,
                'message': 'Section name is required'
            }), 400
        
        success = create_section(data)
        if success:
            return jsonify({
                'success': True,
                'message': f'Section "{data["section"]}" created successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': f'Section "{data["section"]}" already exists'
            }), 409
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating section: {str(e)}'
        }), 500

@content_bp.route('/api/content/<section>', methods=['DELETE'])
def delete_section_content(section):
    """Delete section"""
    if not require_admin():
        return jsonify({
            'success': False,
            'message': 'Admin access required'
        }), 403
    
    try:
        success = delete_section(section)
        if success:
            return jsonify({
                'success': True,
                'message': f'Section "{section}" deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Section "{section}" not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting section: {str(e)}'
        }), 500 
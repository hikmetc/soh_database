"""
Severity of Harm (SoH) Evidence Database - Web Application
A Streamlit-based dashboard for exploring and analyzing SoH meta-analysis data.

Based on: SoH Ordinal Meta-Analysis Method v1.0
Data sources: Cubukcu 2024 (n=514, 195 tests) + Peltier 2025 (n=267, 20 analytes)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="SoH Evidence Database",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .harm-1 { background-color: #2ecc71; }
    .harm-2 { background-color: #f1c40f; }
    .harm-3 { background-color: #e67e22; }
    .harm-4 { background-color: #e74c3c; }
    .harm-5 { background-color: #8e44ad; }
    .info-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3498db;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fef9e7;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f39c12;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data
def load_data():
    """Load all data sheets from the Excel database."""
    from datetime import datetime
    import os

    excel_file = "soh_database_db.xlsx"

    # Get file modification time
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(excel_file))

    data = {
        'study': pd.read_excel(excel_file, sheet_name='study'),
        'scale': pd.read_excel(excel_file, sheet_name='scale'),
        'scale_map': pd.read_excel(excel_file, sheet_name='scale_map'),
        'test_registry': pd.read_excel(excel_file, sheet_name='test_registry'),
        'study_test_result': pd.read_excel(excel_file, sheet_name='study_test_result'),
        'pooled_analysis': pd.read_excel(excel_file, sheet_name='pooled_analysis'),
        'stratum': pd.read_excel(excel_file, sheet_name='stratum'),
        'risk_of_bias': pd.read_excel(excel_file, sheet_name='risk_of_bias'),
        'changelog': pd.read_excel(excel_file, sheet_name='changelog'),
        '_metadata': {
            'loaded_at': datetime.now(),
            'file_modified': file_mod_time
        }
    }
    return data


def get_harm_colors():
    """Return consistent color scheme for SoH levels."""
    return {
        1: '#27ae60',  # Green - Negligible
        2: '#f39c12',  # Yellow - Minor
        3: '#e67e22',  # Orange - Serious
        4: '#e74c3c',  # Red - Critical
        5: '#8e44ad'   # Purple - Catastrophic
    }


def get_harm_labels():
    """Return labels for SoH levels."""
    return {
        1: 'Negligible',
        2: 'Minor',
        3: 'Serious',
        4: 'Critical',
        5: 'Catastrophic'
    }


def wilson_ci(p, n, z=1.96):
    """
    Calculate Wilson score confidence interval for a binomial proportion.

    Based on the SoH Ordinal Meta-Method Manual:
    CI_95% = (p̂ + z²/2n ± z√[p̂(1-p̂)/n + z²/4n²]) / (1 + z²/n)

    Parameters:
    -----------
    p : float
        Observed proportion (0-1 scale, NOT percentage)
    n : int
        Sample size
    z : float
        Z-score for confidence level (default 1.96 for 95% CI)

    Returns:
    --------
    tuple: (lower_bound, upper_bound) as percentages
    """
    if n == 0:
        return (0, 0)

    # Wilson score interval formula
    denominator = 1 + (z**2 / n)
    center = (p + (z**2 / (2 * n))) / denominator
    margin = (z / denominator) * ((p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5)

    lower = max(0, center - margin) * 100  # Convert to percentage
    upper = min(1, center + margin) * 100  # Convert to percentage

    return (lower, upper)


def calculate_all_cis(test_data):
    """
    Calculate Wilson CIs for all SoH categories given test data.

    Parameters:
    -----------
    test_data : pd.Series or dict
        Must contain 'n_total' and 'p1_pct' through 'p5_pct'

    Returns:
    --------
    dict: CIs for each category {1: (lo, hi), 2: (lo, hi), ...}
    """
    n = int(test_data['n_total'])
    cis = {}

    for k in range(1, 6):
        p = test_data[f'p{k}_pct'] / 100  # Convert percentage to proportion
        cis[k] = wilson_ci(p, n)

    return cis


# ============================================================================
# PAGE: DASHBOARD OVERVIEW
# ============================================================================

def page_dashboard(data):
    """Main dashboard overview page."""
    st.markdown('<p class="main-header">Severity of Harm Evidence Database</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Ordinal Meta-Analysis of Laboratory Test Risk Assessment</p>', unsafe_allow_html=True)

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Studies",
            value=len(data['study']),
            help="Number of studies included in the meta-analysis"
        )

    with col2:
        st.metric(
            label="Unique Tests",
            value=len(data['test_registry']),
            help="Total number of unique laboratory tests in the database"
        )

    with col3:
        total_respondents = data['study']['n_total_respondents'].sum()
        st.metric(
            label="Total Respondents",
            value=f"{total_respondents:,}",
            help="Combined number of survey respondents across all studies"
        )

    with col4:
        pooled_tests = len(data['pooled_analysis'][data['pooled_analysis']['n_studies'] > 1])
        st.metric(
            label="Pooled Tests",
            value=pooled_tests,
            help="Tests with data from multiple studies (meta-analyzed)"
        )

    st.markdown("---")

    # Two-column layout for charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("SoH Distribution Overview")

        # Average SoH distribution across all tests
        pooled = data['pooled_analysis']
        avg_dist = [
            pooled['p1_pct'].mean(),
            pooled['p2_pct'].mean(),
            pooled['p3_pct'].mean(),
            pooled['p4_pct'].mean(),
            pooled['p5_pct'].mean()
        ]

        colors = list(get_harm_colors().values())
        labels = list(get_harm_labels().values())

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=avg_dist,
            hole=0.4,
            marker_colors=colors,
            textinfo='label+percent',
            textposition='outside'
        )])
        fig.update_layout(
            title="Average SoH Distribution (All Tests)",
            showlegend=True,
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Tests by Category")

        category_counts = data['test_registry']['category'].value_counts()

        fig = px.bar(
            x=category_counts.values,
            y=category_counts.index,
            orientation='h',
            color=category_counts.values,
            color_continuous_scale='Viridis'
        )
        fig.update_layout(
            xaxis_title="Number of Tests",
            yaxis_title="Category",
            showlegend=False,
            height=400,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # High-risk tests section
    st.markdown("---")
    st.subheader("Highest Risk Tests")
    st.caption("Tests with >50% probability of Critical or Catastrophic harm (P(SoH ≥ 4) > 50%)")

    high_risk = pooled[pooled['p_geq4'] > 50].sort_values('p_geq4', ascending=False).head(10)

    if len(high_risk) > 0:
        # Reverse order so highest-ranked appears at top of chart
        high_risk_reversed = high_risk.iloc[::-1]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=high_risk_reversed['test_canonical'],
            x=high_risk_reversed['p_geq4'],
            orientation='h',
            marker_color='#e74c3c',
            text=[f"{v:.1f}%" for v in high_risk_reversed['p_geq4']],
            textposition='outside'
        ))
        fig.update_layout(
            xaxis_title="Critical/Catastrophic Risk %",
            yaxis_title="",
            height=400,
            xaxis=dict(range=[0, 100])
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No tests with Critical/Catastrophic risk > 50%")

    # Study summary table
    st.markdown("---")
    st.subheader("Included Studies")

    study_display = data['study'][['study_id', 'year', 'country_region', 'design',
                                    'respondent_group', 'n_total_respondents', 'n_analytes']].copy()
    study_display.columns = ['Study ID', 'Year', 'Region', 'Design',
                             'Respondent Group', 'N Respondents', 'N Tests']

    st.dataframe(study_display, use_container_width=True, hide_index=True)


# ============================================================================
# PAGE: POOLED ANALYSIS
# ============================================================================

def page_pooled_analysis(data):
    """Pooled meta-analysis results page."""
    st.markdown('<p class="main-header">Pooled Analysis Results</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Meta-analyzed SoH distributions across studies</p>', unsafe_allow_html=True)

    pooled = data['pooled_analysis'].copy()

    # Filters
    st.sidebar.markdown("### Filters")

    # Category filter
    categories = ['All'] + sorted(pooled['test_category'].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("Test Category", categories)

    # Pooling status filter
    pooling_status = st.sidebar.multiselect(
        "Pooling Status",
        options=['POOLED', 'SINGLE_STUDY'],
        default=['POOLED', 'SINGLE_STUDY']
    )

    # Risk threshold filter
    risk_threshold = st.sidebar.slider(
        "Minimum Critical/Catastrophic Risk %",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        help="P(SoH ≥ 4): Probability that harm is Critical or Catastrophic (levels 4-5)"
    )

    # Apply filters
    if selected_category != 'All':
        pooled = pooled[pooled['test_category'] == selected_category]

    pooled = pooled[pooled['pooling_status'].isin(pooling_status)]
    pooled = pooled[pooled['p_geq4'] >= risk_threshold]

    st.info(f"Showing {len(pooled)} tests")

    # Sort options
    sort_options = [
        'Mean SoH Score (Highest First)',
        'Mean SoH Score (Lowest First)',
        'Critical/Catastrophic Risk (Highest First)',
        'Catastrophic Risk (Highest First)',
        'Catastrophic Risk (Lowest First)',
        'Test Name (A-Z)',
        'Sample Size (Largest First)'
    ]

    sort_by = st.selectbox(
        "Sort by",
        sort_options,
        help="""
        **Mean SoH Score**: Weighted average severity (1-5 scale)
        **Critical/Catastrophic Risk**: P(SoH ≥ 4) - Probability of Critical (4) or Catastrophic (5) harm
        **Catastrophic Risk**: P(SoH = 5) - Probability of Catastrophic harm only
        """
    )

    sort_map = {
        'Mean SoH Score (Highest First)': ('mean_SoH', False),
        'Mean SoH Score (Lowest First)': ('mean_SoH', True),
        'Critical/Catastrophic Risk (Highest First)': ('p_geq4', False),
        'Catastrophic Risk (Highest First)': ('p_eq5', False),
        'Catastrophic Risk (Lowest First)': ('p_eq5', True),
        'Test Name (A-Z)': ('test_canonical', True),
        'Sample Size (Largest First)': ('n_total', False)
    }
    sort_col, ascending = sort_map[sort_by]
    pooled = pooled.sort_values(sort_col, ascending=ascending)

    # Visualization type selection
    viz_type = st.radio(
        "Visualization Type",
        ['Stacked Bar Chart', 'Heat Map', 'Data Table'],
        horizontal=True
    )

    if viz_type == 'Stacked Bar Chart':
        # Stacked bar chart for SoH distribution
        st.subheader("SoH Distribution by Test")

        # Limit to top N for readability
        n_tests = st.slider("Number of tests to display", 5, max(50, len(pooled)), 20)
        display_data = pooled.head(n_tests)

        # Reverse order so highest-ranked appears at top of chart
        display_data_reversed = display_data.iloc[::-1]

        fig = go.Figure()

        colors = get_harm_colors()
        labels = get_harm_labels()

        for level in [1, 2, 3, 4, 5]:
            fig.add_trace(go.Bar(
                name=f'{level} - {labels[level]}',
                y=display_data_reversed['test_canonical'],
                x=display_data_reversed[f'p{level}_pct'],
                orientation='h',
                marker_color=colors[level],
                hovertemplate=f"<b>{labels[level]}</b><br>%{{x:.1f}}%<extra></extra>"
            ))

        fig.update_layout(
            barmode='stack',
            height=max(400, n_tests * 25),
            xaxis_title="Percentage (%)",
            yaxis_title="",
            legend_title="SoH Level",
            xaxis=dict(range=[0, 100])
        )

        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == 'Heat Map':
        st.subheader("SoH Distribution Heat Map")

        # Pivot for heatmap
        n_tests = st.slider("Number of tests to display", 5, max(50, len(pooled)), 20)
        display_data = pooled.head(n_tests)

        # Note: px.imshow displays y-axis top-to-bottom (first item at top)
        # so NO reversal needed here (unlike horizontal bar charts)

        fig = px.imshow(
            display_data[['p1_pct', 'p2_pct', 'p3_pct', 'p4_pct', 'p5_pct']].values,
            y=display_data['test_canonical'].tolist(),
            x=['Negligible', 'Minor', 'Serious', 'Critical', 'Catastrophic'],
            color_continuous_scale='RdYlGn_r',
            aspect='auto'
        )

        fig.update_layout(
            height=max(400, n_tests * 20),
            xaxis_title="SoH Category",
            yaxis_title=""
        )

        st.plotly_chart(fig, use_container_width=True)

    else:  # Data Table
        st.subheader("Pooled Analysis Data")

        # Legend for probability columns
        st.caption("""
        **Column Legend:**
        • **Crit/Cat Risk %** = P(SoH ≥ 4): Probability of Critical or Catastrophic harm
        • **Catastrophic %** = P(SoH = 5): Probability of Catastrophic harm only
        """)

        display_cols = [
            'test_canonical', 'test_category', 'n_studies', 'n_total',
            'p1_pct', 'p2_pct', 'p3_pct', 'p4_pct', 'p5_pct',
            'mean_SoH', 'median_SoH', 'mode_SoH', 'p_geq4', 'p_eq5', 'pooling_status'
        ]

        display_df = pooled[display_cols].copy()
        display_df.columns = [
            'Test', 'Category', 'Studies', 'N Total',
            '% Negligible', '% Minor', '% Serious', '% Critical', '% Catastrophic',
            'Mean SoH', 'Median', 'Mode', 'Crit/Cat Risk %', 'Catastrophic %', 'Status'
        ]

        # Format numeric columns
        for col in ['% Negligible', '% Minor', '% Serious', '% Critical', '% Catastrophic', 'Crit/Cat Risk %', 'Catastrophic %']:
            display_df[col] = display_df[col].round(1)
        display_df['Mean SoH'] = display_df['Mean SoH'].round(2)

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Download option
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="soh_pooled_analysis.csv",
            mime="text/csv"
        )


# ============================================================================
# PAGE: TEST EXPLORER
# ============================================================================

def page_test_explorer(data):
    """Detailed view for individual tests."""
    st.markdown('<p class="main-header">Test Explorer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Detailed SoH analysis for individual laboratory tests</p>', unsafe_allow_html=True)

    pooled = data['pooled_analysis']
    study_results = data['study_test_result']

    # Test selection
    test_options = sorted(pooled['test_canonical'].unique().tolist())
    selected_test = st.selectbox("Select a Test", test_options)

    # Get data for selected test
    test_data = pooled[pooled['test_canonical'] == selected_test].iloc[0]

    # Header info
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Test Category", test_data['test_category'])
    with col2:
        st.metric("Specimen Matrix", test_data['specimen_matrix'])
    with col3:
        st.metric("Number of Studies", test_data['n_studies'])

    st.markdown("---")

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Mean SoH",
            f"{test_data['mean_SoH']:.2f}",
            help="Weighted mean severity of harm score (1-5 scale)"
        )

    with col2:
        st.metric(
            "Median SoH",
            f"{test_data['median_SoH']:.0f}",
            help="Median severity of harm category"
        )

    with col3:
        st.metric(
            "Critical/Catastrophic Risk",
            f"{test_data['p_geq4']:.1f}%",
            help="P(SoH ≥ 4): Probability that harm severity is Critical (level 4) or Catastrophic (level 5)"
        )

    with col4:
        st.metric(
            "Catastrophic Risk",
            f"{test_data['p_eq5']:.1f}%",
            help="P(SoH = 5): Probability that harm severity is Catastrophic (level 5 - life-threatening/death)"
        )

    st.markdown("---")

    # Distribution visualization
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("SoH Distribution")

        colors = list(get_harm_colors().values())
        labels = list(get_harm_labels().values())
        values = [test_data['p1_pct'], test_data['p2_pct'], test_data['p3_pct'],
                  test_data['p4_pct'], test_data['p5_pct']]

        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[f'{v:.1f}%' for v in values],
            textposition='outside'
        )])

        fig.update_layout(
            xaxis_title="SoH Category",
            yaxis_title="Percentage (%)",
            yaxis=dict(range=[0, max(values) * 1.2]),
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Distribution with 95% CI")

        # Calculate Wilson CIs for all categories
        cis = calculate_all_cis(test_data)

        # Show all 5 categories with their CIs
        categories = list(get_harm_labels().values())
        values = [test_data[f'p{k}_pct'] for k in range(1, 6)]
        colors = list(get_harm_colors().values())
        lower = [cis[k][0] for k in range(1, 6)]
        upper = [cis[k][1] for k in range(1, 6)]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            error_y=dict(
                type='data',
                symmetric=False,
                array=[u - v for u, v in zip(upper, values)],
                arrayminus=[v - l for v, l in zip(values, lower)]
            ),
            text=[f'{v:.1f}%' for v in values],
            textposition='outside'
        ))

        fig.update_layout(
            xaxis_title="SoH Category",
            yaxis_title="Percentage (%)",
            yaxis=dict(range=[0, max(upper) * 1.3 if max(upper) > 0 else 100]),
            height=400
        )
        st.caption(f"Wilson 95% CI based on n={int(test_data['n_total'])} respondents")

        st.plotly_chart(fig, use_container_width=True)

    # Per-study breakdown (if multiple studies)
    if test_data['n_studies'] > 1:
        st.markdown("---")
        st.subheader("Study-Level Comparison")

        # Get test_id from test_registry
        test_registry = data['test_registry']
        test_id = test_registry[test_registry['test_canonical'] == selected_test]['test_id'].values[0]

        # Get per-study results
        study_data = study_results[study_results['test_id'] == test_id]

        fig = go.Figure()

        for _, row in study_data.iterrows():
            study_id = row['study_id']
            values = [row['p1_pct'], row['p2_pct'], row['p3_pct'], row['p4_pct'], row['p5_pct']]

            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],  # Close the polygon
                theta=list(get_harm_labels().values()) + [list(get_harm_labels().values())[0]],
                fill='toself',
                name=study_id,
                opacity=0.6
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100])
            ),
            showlegend=True,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Table comparison
        st.subheader("Detailed Study Comparison")

        comparison_df = study_data[['study_id', 'n_raters_test', 'p1_pct', 'p2_pct',
                                     'p3_pct', 'p4_pct', 'p5_pct', 'mean_SoH']].copy()
        comparison_df.columns = ['Study', 'N Raters', '% Negligible', '% Minor',
                                  '% Serious', '% Critical', '% Catastrophic', 'Mean SoH']

        for col in ['% Negligible', '% Minor', '% Serious', '% Critical', '% Catastrophic']:
            comparison_df[col] = comparison_df[col].round(1)
        comparison_df['Mean SoH'] = comparison_df['Mean SoH'].round(2)

        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"This test has data from a single study ({test_data['study_ids']})")


# ============================================================================
# PAGE: STUDY COMPARISON
# ============================================================================

def page_study_comparison(data):
    """Compare SoH ratings between studies."""
    st.markdown('<p class="main-header">Study Comparison</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Compare SoH ratings between Cubukcu 2024 and Peltier 2025</p>', unsafe_allow_html=True)

    study_results = data['study_test_result']
    pooled = data['pooled_analysis']

    # Get overlapping tests
    overlapping = pooled[pooled['n_studies'] > 1]['test_canonical'].tolist()

    st.info(f"There are {len(overlapping)} tests with data from both studies")

    # Comparison visualization
    st.subheader("Mean SoH Comparison")

    comparison_data = []
    for test in overlapping:
        test_results = study_results[study_results['test_name_original'].str.contains(test.split(' (')[0], case=False, na=False)]

        cub_data = test_results[test_results['study_id'] == 'CUB2024']
        pel_data = test_results[test_results['study_id'] == 'PEL2025']

        if len(cub_data) > 0 and len(pel_data) > 0:
            comparison_data.append({
                'Test': test,
                'CUB2024': cub_data['mean_SoH'].values[0],
                'PEL2025': pel_data['mean_SoH'].values[0]
            })

    if comparison_data:
        comp_df = pd.DataFrame(comparison_data)
        comp_df['Difference'] = comp_df['PEL2025'] - comp_df['CUB2024']
        comp_df = comp_df.sort_values('Difference')

        # Scatter plot
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=comp_df['CUB2024'],
            y=comp_df['PEL2025'],
            mode='markers+text',
            text=comp_df['Test'].apply(lambda x: x[:20] + '...' if len(x) > 20 else x),
            textposition='top center',
            marker=dict(
                size=12,
                color=comp_df['Difference'],
                colorscale='RdBu_r',
                colorbar=dict(title='Difference<br>(PEL - CUB)'),
                showscale=True
            ),
            hovertemplate="<b>%{text}</b><br>CUB2024: %{x:.2f}<br>PEL2025: %{y:.2f}<extra></extra>"
        ))

        # Add diagonal line
        fig.add_trace(go.Scatter(
            x=[1, 5],
            y=[1, 5],
            mode='lines',
            line=dict(dash='dash', color='gray'),
            showlegend=False
        ))

        fig.update_layout(
            xaxis_title="Mean SoH - Cubukcu 2024 (Clinicians)",
            yaxis_title="Mean SoH - Peltier 2025 (Lab Professionals)",
            height=600,
            xaxis=dict(range=[1, 5]),
            yaxis=dict(range=[1, 5])
        )

        st.plotly_chart(fig, use_container_width=True)

        # Difference bar chart
        st.subheader("Rating Differences (PEL2025 - CUB2024)")

        fig2 = go.Figure()

        colors = ['#e74c3c' if d < 0 else '#27ae60' for d in comp_df['Difference']]

        fig2.add_trace(go.Bar(
            y=comp_df['Test'],
            x=comp_df['Difference'],
            orientation='h',
            marker_color=colors,
            text=[f'{d:+.2f}' for d in comp_df['Difference']],
            textposition='outside'
        ))

        fig2.add_vline(x=0, line_dash="dash", line_color="gray")

        fig2.update_layout(
            xaxis_title="Difference in Mean SoH",
            yaxis_title="",
            height=max(400, len(comp_df) * 30)
        )

        st.plotly_chart(fig2, use_container_width=True)

        # Summary statistics
        st.markdown("---")
        st.subheader("Summary Statistics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Average Difference",
                f"{comp_df['Difference'].mean():+.2f}",
                help="Mean difference in SoH ratings (PEL2025 - CUB2024)"
            )

        with col2:
            higher_pel = (comp_df['Difference'] > 0).sum()
            st.metric(
                "Higher in PEL2025",
                f"{higher_pel}/{len(comp_df)} tests",
                help="Number of tests rated higher by lab professionals"
            )

        with col3:
            corr = comp_df['CUB2024'].corr(comp_df['PEL2025'])
            st.metric(
                "Correlation",
                f"r = {corr:.3f}",
                help="Pearson correlation between study ratings"
            )
    else:
        st.warning("Could not find matching test data for comparison")


# ============================================================================
# PAGE: RISK OF BIAS
# ============================================================================

def page_risk_of_bias(data):
    """Risk of bias assessment page."""
    st.markdown('<p class="main-header">Risk of Bias Assessment</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Quality assessment of included studies</p>', unsafe_allow_html=True)

    rob = data['risk_of_bias']
    studies = data['study']

    # Color mapping for ratings
    rating_colors = {
        'Low (good)': '#27ae60',
        'Moderate': '#f39c12',
        'High': '#e74c3c'
    }

    # Study-wise assessment
    for study_id in rob['study_id'].unique():
        study_info = studies[studies['study_id'] == study_id].iloc[0]
        study_rob = rob[rob['study_id'] == study_id]

        with st.expander(f"**{study_id}** - {study_info['year']}", expanded=True):
            st.write(f"**Region:** {study_info['country_region']}")
            st.write(f"**Design:** {study_info['design']}")
            st.write(f"**Respondents:** {study_info['respondent_group']} (n={study_info['n_total_respondents']})")

            st.markdown("---")

            for _, row in study_rob.iterrows():
                col1, col2 = st.columns([1, 3])

                with col1:
                    color = rating_colors.get(row['rating'], '#666')
                    st.markdown(
                        f'<span style="background-color: {color}; color: white; '
                        f'padding: 4px 8px; border-radius: 4px; font-weight: bold;">'
                        f'{row["rating"]}</span>',
                        unsafe_allow_html=True
                    )

                with col2:
                    st.write(f"**{row['domain']}**")
                    st.write(row['justification'])

    # Summary visualization
    st.markdown("---")
    st.subheader("Risk of Bias Summary")

    # Create summary matrix
    domains = rob['domain'].unique()
    study_ids = rob['study_id'].unique()

    summary_data = []
    for study in study_ids:
        for domain in domains:
            rating = rob[(rob['study_id'] == study) & (rob['domain'] == domain)]['rating'].values
            if len(rating) > 0:
                summary_data.append({
                    'Study': study,
                    'Domain': domain,
                    'Rating': rating[0],
                    'Score': {'Low (good)': 1, 'Moderate': 2, 'High': 3}.get(rating[0], 2)
                })

    summary_df = pd.DataFrame(summary_data)
    pivot_df = summary_df.pivot(index='Domain', columns='Study', values='Score')

    fig = px.imshow(
        pivot_df.values,
        x=pivot_df.columns.tolist(),
        y=pivot_df.index.tolist(),
        color_continuous_scale=[[0, '#27ae60'], [0.5, '#f39c12'], [1, '#e74c3c']],
        aspect='auto'
    )

    fig.update_layout(
        height=400,
        xaxis_title="Study",
        yaxis_title="Domain",
        coloraxis_colorbar=dict(
            title="Risk",
            tickvals=[1, 2, 3],
            ticktext=['Low', 'Moderate', 'High']
        )
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# PAGE: METHODOLOGY
# ============================================================================

def page_methodology(data):
    """Methodology and scale information page."""
    st.markdown('<p class="main-header">Methodology</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Statistical methods and scale harmonization</p>', unsafe_allow_html=True)

    # Canonical scale
    st.subheader("Canonical SoH Scale")

    scale_df = pd.DataFrame({
        'Code': [1, 2, 3, 4, 5],
        'Label': ['Negligible', 'Minor', 'Serious', 'Critical', 'Catastrophic'],
        'Description': [
            'No significant harm expected from erroneous result interpretation',
            'Temporary discomfort or minor additional testing required',
            'Temporary harm requiring treatment or extended stay',
            'Permanent harm, significant intervention, or disability',
            'Life-threatening condition or death possible'
        ],
        'Reference': ['ISO 14971:2019 and ISO 24971:2020 / CLSI EP23'] * 5
    })

    st.dataframe(scale_df, use_container_width=True, hide_index=True)

    # Scale harmonization
    #st.markdown("---")
    #st.subheader("Scale Harmonization")

    #st.write("Different studies may use different terminology. The following mappings are applied:")

    #scale_map = data['scale_map'][['from_scale', 'orig_level', 'canon_code', 'canon_label', 'rule']]
    #scale_map.columns = ['Original Scale', 'Original Level', 'Canonical Code', 'Canonical Label', 'Rule']

    #st.dataframe(scale_map, use_container_width=True, hide_index=True)

    # Pooling methodology
    st.markdown("---")
    st.subheader("Direct Count Pooling Method")

    st.markdown("""
    The primary pooling method is **Direct Count Pooling**, which calculates pooled proportions
    by summing category counts across studies.
    """)

    # Step 1
    st.markdown("**Step 1 — Aggregate Counts**")
    st.markdown("For each test *t*, category counts are summed across all studies (*s*):")
    st.latex(r"C_k(t) = \sum_{s} c_{k,s,t} \quad \text{for } k = 1, 2, 3, 4, 5")
    st.latex(r"N(t) = \sum_{k=1}^{5} C_k(t)")

    # Step 2
    st.markdown("**Step 2 — Calculate Pooled Proportions**")
    st.latex(r"p_k(t) = \frac{C_k(t)}{N(t)} \quad \text{for each category } k")

    # Step 3
    st.markdown("**Step 3 — Confidence Intervals**")
    st.markdown("95% confidence intervals are calculated using the **Wilson method** for binomial proportions:")
    st.latex(r"\text{CI}_{95\%} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}")
    st.caption("where *z* = 1.96 for 95% confidence level")

    # Derived Metrics
    st.markdown("---")
    st.markdown("**Derived Metrics**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("*Mean SoH Score (weighted average):*")
        st.latex(r"E[\text{SoH}] = \sum_{k=1}^{5} k \cdot p_k = 1 \cdot p_1 + 2 \cdot p_2 + 3 \cdot p_3 + 4 \cdot p_4 + 5 \cdot p_5")

        st.markdown("*Critical/Catastrophic Risk:*")
        st.latex(r"P(\text{SoH} \geq 4) = p_4 + p_5")

    with col1:
        st.markdown("*Catastrophic Risk:*")
        st.latex(r"P(\text{SoH} = 5) = p_5")

        st.markdown("*Mode (most frequent category):*")
        st.latex(r"\text{Mode} = \arg\max_k \, p_k")

        st.markdown("*Median (50th percentile):*")
        st.latex(r"\text{Median} = \min \left\{ k : \sum_{i=1}^{k} p_i \geq 0.5 \right\}")

    # Stratum information
    st.markdown("---")
    st.subheader("Respondent Strata")

    stratum = data['stratum'][['stratum_id', 'study_id', 'stratum_label', 'n_stratum', 'description']]
    stratum.columns = ['Stratum ID', 'Study', 'Label', 'N', 'Description']

    st.dataframe(stratum, use_container_width=True, hide_index=True)


# ============================================================================
# PAGE: DATA DOWNLOAD
# ============================================================================

def page_data_download(data):
    """Data download page."""
    st.markdown('<p class="main-header">Data Download</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Export database tables for further analysis</p>', unsafe_allow_html=True)

    st.markdown("""
    Download the complete database or individual tables in CSV format for your own analysis.
    All data follows the SoH Ordinal Meta-Method v1.0 specification.
    """)

    # Table descriptions
    table_info = {
        'study': 'Study-level metadata including DOI, design, respondent information, and scale used',
        'test_registry': 'Canonical test list with 196 unique laboratory tests',
        'study_test_result': 'Per-study-test SoH distributions (c1-c5, p1-p5) and derived statistics',
        'pooled_analysis': 'Meta-analyzed pooled results with confidence intervals',
        'scale': 'Scale definitions used by each study',
        'scale_map': 'Mapping rules from original scales to canonical 1-5 scale',
        'stratum': 'Respondent subgroup definitions',
        'risk_of_bias': 'Risk of bias assessment for each study',
        'changelog': 'Database version history and corrections'
    }

    for table_name, description in table_info.items():
        with st.expander(f"**{table_name}** - {len(data[table_name])} rows"):
            st.write(description)
            st.write(f"**Columns:** {', '.join(data[table_name].columns.tolist())}")

            # Preview
            st.dataframe(data[table_name].head(5), use_container_width=True, hide_index=True)

            # Download button
            csv = data[table_name].to_csv(index=False)
            st.download_button(
                label=f"Download {table_name}.csv",
                data=csv,
                file_name=f"soh_{table_name}.csv",
                mime="text/csv"
            )

    # Full database download
    st.markdown("---")
    st.subheader("Download Complete Database")

    # Create combined CSV
    import io
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for table_name, df in data.items():
            df.to_excel(writer, sheet_name=table_name, index=False)

    st.download_button(
        label="Download Complete Database (Excel)",
        data=output.getvalue(),
        file_name="soh_evidence_database_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application entry point."""

    # Load data
    try:
        data = load_data()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Please ensure 'soh_database_db.xlsx' is in the same directory as this application.")
        return

    # Sidebar navigation
    st.sidebar.image("https://img.icons8.com/fluency/96/test-tube.png", width=80)
    st.sidebar.title("SoH Evidence Database")
    st.sidebar.markdown("---")

    pages = {
        "Dashboard": page_dashboard,
        "Pooled Analysis": page_pooled_analysis,
        "Test Explorer": page_test_explorer,
        "Study Comparison": page_study_comparison,
        "Risk of Bias": page_risk_of_bias,
        "Methodology": page_methodology,
        "Data Download": page_data_download
    }

    selection = st.sidebar.radio("Navigation", list(pages.keys()))

    # Update data button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True, help="Reload data from the database file"):
        st.cache_data.clear()
        st.rerun()

    # Show data load info
    if '_metadata' in data:
        loaded_at = data['_metadata']['loaded_at'].strftime("%H:%M:%S")
        file_mod = data['_metadata']['file_modified'].strftime("%Y-%m-%d %H:%M")
        st.sidebar.caption(f"📊 Data loaded: {loaded_at}")
        st.sidebar.caption(f"📁 File modified: {file_mod}")

    # Render selected page
    pages[selection](data)

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <small>
    **Database v1.1**<br>
    Based on SoH Ordinal Meta-Method v1.0<br>
    <br>
    Studies: Cubukcu 2024, Peltier 2025<br>
    196 tests | 781 total respondents
    </small>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

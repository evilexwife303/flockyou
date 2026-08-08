library(shiny)
library(leaflet)
library(sf)
library(dplyr)

# Load the master dataset
data_path <- "../data/processed/master_alpr_dragnet.geojson"
master_data <- st_read(data_path)

ui <- fluidPage(
  titlePanel("Flock Accountability: ALPR Dragnet Analysis"),
  sidebarLayout(
    sidebarPanel(
      helpText("Visualizing surveillance intersection with sensitive sites."),
      selectInput("color_var", "Visualize by Variable:", 
                  choices = c("pct_poverty", "pct_black", "pct_hispanic", "pct_non_citizen")),
      hr(),
      verbatimTextOutput("stats")
    ),
    mainPanel(
      leafletOutput("map", height = "80vh")
    )
  )
)

server <- function(input, output, session) {
  output$map <- renderLeaflet({
    pal <- colorNumeric("YlOrRd", domain = master_data[[input$color_var]])
    
    leaflet(master_data) %>%
      addProviderTiles(providers$CartoDB.Positron) %>%
      addCircleMarkers(
        radius = 5,
        color = ~pal(get(input$color_var)),
        popup = ~paste0("<b>Site:</b> ", surveilled_sites_list, "<br><b>Poverty:</b> ", round(pct_poverty, 1), "%")
      )
  })
}

shinyApp(ui, server)
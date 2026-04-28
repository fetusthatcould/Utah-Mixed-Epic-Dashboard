using Microsoft.AspNetCore.Mvc;
using Npgsql;
using Dapper;
using Ume.Intelligence.Api.Models;

namespace Ume.Intelligence.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RouteController : ControllerBase
{
    private readonly IConfiguration _config;

    public RouteController(IConfiguration config)
    {
        _config = config;
    }

    [HttpGet("intelligence")]
    public async Task<IActionResult> GetEnrichedRoute()
    {
        using var connection = new NpgsqlConnection(_config.GetConnectionString("PostGIS"));
        
        // We query your UI View v_ui_route_layer directly.
        // ST_AsGeoJSON converts the PostGIS geometry into a format Mapbox understands.
        const string sql = @"
           SELECT 
            PointOrder,
            ElevationM,
            SlopePctSmooth,
            TechScore,
            LandCoverType,
            CumulativeFatigueIndex,
            FoodScore,
            WaterScore,
            ST_AsGeoJSON(geom_4326) as GeoJson
        FROM v_ui_route_layer
        ORDER BY PointOrder ASC
       ";

        try
        {
            var points = await connection.QueryAsync<RacePoint>(sql);
            return Ok(points);
        }
        catch (Exception ex)
        {
            return StatusCode(500, $"Internal server error: {ex.Message}");
        }
    }
}